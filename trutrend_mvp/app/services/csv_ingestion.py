"""CSV file ingestion and processing service."""

import csv
import hashlib
import logging
from datetime import datetime
from io import StringIO
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

from ..models.data_models import DeviceType, PatientData, GlucoseReading, InsulinEvent, CarbEvent
from ..core.exceptions import DataIngestionError
from ..core.security import security_manager

logger = logging.getLogger(__name__)


class CSVIngestionService:
    """Handles CSV file ingestion with auto-detection and validation."""
    
    def __init__(self):
        self.device_patterns = {
            DeviceType.DEXCOM: {
                'required_columns': ['timestamp', 'glucose_value'],
                'timestamp_formats': ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M'],
                'glucose_column': 'glucose_value'
            },
            DeviceType.LIBREVIEW: {
                'required_columns': ['time', 'historic_glucose'],
                'timestamp_formats': ['%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S'],
                'glucose_column': 'historic_glucose'
            },
            DeviceType.GLOOKO: {
                'required_columns': ['timestamp', 'bg_value'],
                'timestamp_formats': ['%Y-%m-%d %H:%M:%S'],
                'glucose_column': 'bg_value'
            }
        }
    
    async def process_csv_file(self, file_content: str, patient_id: str, 
                              suggested_device: DeviceType = DeviceType.UNKNOWN) -> PatientData:
        """Process uploaded CSV file and return normalized data."""
        try:
            # Auto-detect device type if not specified
            device_type = await self._detect_device_type(file_content)
            if suggested_device != DeviceType.UNKNOWN:
                device_type = suggested_device
            
            # Parse CSV content
            df = pd.read_csv(StringIO(file_content))
            logger.info(f"Loaded CSV with {len(df)} rows for patient {patient_id}")
            
            # Normalize data based on device type
            normalized_data = await self._normalize_csv_data(df, device_type, patient_id)
            
            # Validate data quality
            await self._validate_data_quality(normalized_data)
            
            return normalized_data
            
        except Exception as e:
            logger.error(f"CSV processing failed for patient {patient_id}: {e}")
            raise DataIngestionError(f"Failed to process CSV file: {e}")
    
    async def _detect_device_type(self, file_content: str) -> DeviceType:
        """Auto-detect device type from CSV headers and content patterns."""
        try:
            # Read first few lines to analyze headers
            lines = file_content.split('\n')[:5]
            header_content = '\n'.join(lines).lower()
            
            # Check for device-specific patterns
            if 'dexcom' in header_content or 'cgm' in header_content:
                return DeviceType.DEXCOM
            elif 'libre' in header_content or 'abbott' in header_content:
                return DeviceType.LIBREVIEW
            elif 'glooko' in header_content:
                return DeviceType.GLOOKO
            elif 'tandem' in header_content:
                return DeviceType.TANDEM
            elif 'medtronic' in header_content:
                return DeviceType.MEDTRONIC
            
            # Fallback: analyze column patterns
            df_sample = pd.read_csv(StringIO(file_content), nrows=10)
            columns = [col.lower().strip() for col in df_sample.columns]
            
            for device_type, pattern in self.device_patterns.items():
                required_cols = [col.lower() for col in pattern['required_columns']]
                if all(any(req_col in col for col in columns) for req_col in required_cols):
                    return device_type
            
            logger.warning("Could not auto-detect device type, using UNKNOWN")
            return DeviceType.UNKNOWN
            
        except Exception as e:
            logger.error(f"Device detection failed: {e}")
            return DeviceType.UNKNOWN
    
    async def _normalize_csv_data(self, df: pd.DataFrame, device_type: DeviceType, 
                                 patient_id: str) -> PatientData:
        """Normalize CSV data to standard format."""
        glucose_readings = []
        insulin_events = []
        carb_events = []
        
        # Device-specific column mapping
        column_mapping = self._get_column_mapping(device_type, df.columns)
        
        for _, row in df.iterrows():
            try:
                # Parse timestamp
                timestamp = await self._parse_timestamp(
                    row, column_mapping.get('timestamp'), device_type
                )
                
                # Extract glucose reading
                if column_mapping.get('glucose'):
                    glucose_value = self._safe_float_conversion(row[column_mapping['glucose']])
                    if glucose_value and 20 <= glucose_value <= 600:
                        glucose_readings.append(GlucoseReading(
                            timestamp=timestamp,
                            glucose_value=glucose_value,
                            device_type=device_type,
                            trend_arrow=row.get('trend_arrow', None)
                        ))
                
                # Extract insulin events
                if column_mapping.get('insulin_bolus'):
                    bolus_units = self._safe_float_conversion(row[column_mapping['insulin_bolus']])
                    if bolus_units and bolus_units > 0:
                        insulin_events.append(InsulinEvent(
                            timestamp=timestamp,
                            insulin_type='bolus',
                            units=bolus_units
                        ))
                
                if column_mapping.get('insulin_basal'):
                    basal_units = self._safe_float_conversion(row[column_mapping['insulin_basal']])
                    if basal_units and basal_units > 0:
                        insulin_events.append(InsulinEvent(
                            timestamp=timestamp,
                            insulin_type='basal',
                            units=basal_units
                        ))
                
                # Extract carb events
                if column_mapping.get('carbs'):
                    carb_value = self._safe_float_conversion(row[column_mapping['carbs']])
                    if carb_value and carb_value > 0:
                        carb_events.append(CarbEvent(
                            timestamp=timestamp,
                            carbs=carb_value,
                            meal_type=row.get('meal_type', None)
                        ))
                        
            except Exception as e:
                logger.warning(f"Failed to process row: {e}")
                continue
        
        # Determine data date range
        all_timestamps = [g.timestamp for g in glucose_readings]
        if insulin_events:
            all_timestamps.extend([i.timestamp for i in insulin_events])
        if carb_events:
            all_timestamps.extend([c.timestamp for c in carb_events])
        
        data_start_date = min(all_timestamps) if all_timestamps else datetime.utcnow()
        data_end_date = max(all_timestamps) if all_timestamps else datetime.utcnow()
        
        return PatientData(
            patient_id=patient_id,
            glucose_readings=glucose_readings,
            insulin_events=insulin_events,
            carb_events=carb_events,
            device_type=device_type,
            upload_timestamp=datetime.utcnow(),
            data_start_date=data_start_date,
            data_end_date=data_end_date
        )
    
    def _get_column_mapping(self, device_type: DeviceType, columns: List[str]) -> Dict[str, str]:
        """Map CSV columns to standard fields based on device type."""
        columns_lower = [col.lower().strip() for col in columns]
        mapping = {}
        
        # Common patterns for different data types
        timestamp_patterns = ['timestamp', 'time', 'datetime', 'date']
        glucose_patterns = ['glucose', 'bg', 'blood_glucose', 'glucose_value', 'bg_value']
        insulin_bolus_patterns = ['bolus', 'insulin_bolus', 'rapid_insulin']
        insulin_basal_patterns = ['basal', 'insulin_basal', 'long_insulin']
        carb_patterns = ['carbs', 'carbohydrates', 'carb_grams']
        
        # Find best matches
        for col in columns_lower:
            if not mapping.get('timestamp') and any(pattern in col for pattern in timestamp_patterns):
                mapping['timestamp'] = columns[columns_lower.index(col)]
            elif not mapping.get('glucose') and any(pattern in col for pattern in glucose_patterns):
                mapping['glucose'] = columns[columns_lower.index(col)]
            elif not mapping.get('insulin_bolus') and any(pattern in col for pattern in insulin_bolus_patterns):
                mapping['insulin_bolus'] = columns[columns_lower.index(col)]
            elif not mapping.get('insulin_basal') and any(pattern in col for pattern in insulin_basal_patterns):
                mapping['insulin_basal'] = columns[columns_lower.index(col)]
            elif not mapping.get('carbs') and any(pattern in col for pattern in carb_patterns):
                mapping['carbs'] = columns[columns_lower.index(col)]
        
        return mapping
    
    async def _parse_timestamp(self, row: pd.Series, timestamp_col: Optional[str], 
                              device_type: DeviceType) -> datetime:
        """Parse timestamp from row data."""
        if not timestamp_col or pd.isna(row[timestamp_col]):
            raise ValueError("Missing timestamp")
        
        timestamp_str = str(row[timestamp_col]).strip()
        formats_to_try = self.device_patterns.get(device_type, {}).get(
            'timestamp_formats', ['%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M', '%d/%m/%Y %H:%M']
        )
        
        for fmt in formats_to_try:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # Fallback: try pandas parsing
        try:
            return pd.to_datetime(timestamp_str)
        except Exception:
            raise ValueError(f"Could not parse timestamp: {timestamp_str}")
    
    def _safe_float_conversion(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if pd.isna(value) or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    async def _validate_data_quality(self, data: PatientData):
        """Validate data quality and completeness."""
        if not data.glucose_readings:
            raise DataIngestionError("No valid glucose readings found")
        
        if len(data.glucose_readings) < 10:
            logger.warning(f"Low glucose reading count: {len(data.glucose_readings)}")
        
        # Check for reasonable time span
        time_span = (data.data_end_date - data.data_start_date).days
        if time_span < 1:
            logger.warning("Data spans less than 1 day")
        elif time_span > 90:
            logger.warning(f"Data spans {time_span} days - unusually long")
        
        logger.info(f"Data quality validation passed: {len(data.glucose_readings)} glucose readings, "
                   f"{len(data.insulin_events)} insulin events, {len(data.carb_events)} carb events")


# Temporary security manager stub
class SecurityManager:
    def log_audit_event(self, event_type, user_id, patient_id=None, details=None):
        logger.info(f"Audit: {event_type} by {user_id}")

security_manager = SecurityManager()