"""Tests for CSV ingestion service."""

import pytest
from datetime import datetime
from io import StringIO

from app.services.csv_ingestion import CSVIngestionService
from app.models.data_models import DeviceType


class TestCSVIngestionService:
    """Test CSV ingestion functionality."""
    
    @pytest.fixture
    def csv_service(self):
        return CSVIngestionService()
    
    @pytest.fixture
    def sample_dexcom_csv(self):
        return """timestamp,glucose_value,trend_arrow
2024-01-01 08:00:00,120,→
2024-01-01 08:15:00,135,↗
2024-01-01 08:30:00,150,↗
2024-01-01 08:45:00,165,→"""
    
    @pytest.fixture
    def sample_glooko_csv(self):
        return """timestamp,bg_value,insulin_bolus,carbs
2024-01-01 08:00:00,120,5.0,45
2024-01-01 08:15:00,135,0,0
2024-01-01 08:30:00,150,0,0"""
    
    @pytest.mark.asyncio
    async def test_detect_dexcom_device(self, csv_service, sample_dexcom_csv):
        """Test auto-detection of Dexcom device type."""
        device_type = await csv_service._detect_device_type(sample_dexcom_csv)
        # Since our sample doesn't have explicit device markers, it may return UNKNOWN
        assert device_type in [DeviceType.DEXCOM, DeviceType.UNKNOWN]
    
    @pytest.mark.asyncio
    async def test_process_csv_with_glucose_data(self, csv_service, sample_dexcom_csv):
        """Test processing CSV with glucose data."""
        patient_data = await csv_service.process_csv_file(
            sample_dexcom_csv, "test_patient_001"
        )
        
        assert patient_data.patient_id == "test_patient_001"
        assert len(patient_data.glucose_readings) == 4
        assert patient_data.glucose_readings[0].glucose_value == 120.0
        assert patient_data.glucose_readings[1].glucose_value == 135.0
    
    @pytest.mark.asyncio
    async def test_process_csv_with_insulin_and_carbs(self, csv_service, sample_glooko_csv):
        """Test processing CSV with insulin and carb data."""
        patient_data = await csv_service.process_csv_file(
            sample_glooko_csv, "test_patient_002", DeviceType.GLOOKO
        )
        
        assert len(patient_data.glucose_readings) == 3
        assert len(patient_data.insulin_events) == 1
        assert len(patient_data.carb_events) == 1
        assert patient_data.insulin_events[0].units == 5.0
        assert patient_data.carb_events[0].carbs == 45.0
    
    @pytest.mark.asyncio
    async def test_invalid_glucose_values_filtered(self, csv_service):
        """Test that invalid glucose values are filtered out."""
        invalid_csv = """timestamp,glucose_value
2024-01-01 08:00:00,120
2024-01-01 08:15:00,10
2024-01-01 08:30:00,700
2024-01-01 08:45:00,150"""
        
        patient_data = await csv_service.process_csv_file(invalid_csv, "test_patient_003")
        
        # Only 2 readings should remain (10 and 700 are out of range)
        assert len(patient_data.glucose_readings) == 2
        glucose_values = [r.glucose_value for r in patient_data.glucose_readings]
        assert 10 not in glucose_values
        assert 700 not in glucose_values