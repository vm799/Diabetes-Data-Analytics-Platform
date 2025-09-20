"""Clinical analytics engine implementing diabetes pattern detection rules."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import statistics

from ..models.data_models import PatientData, AnalyticsResult, GlucoseReading, InsulinEvent, CarbEvent
from ..core.config import settings
from ..core.exceptions import AnalyticsError

logger = logging.getLogger(__name__)


class ClinicalAnalyticsEngine:
    """Implements clinical rules for diabetes pattern detection."""
    
    def __init__(self):
        self.rules = {
            'postprandial_hyperglycemia': self._detect_postprandial_hyperglycemia,
            'mistimed_bolus': self._detect_mistimed_bolus,
            'carb_ratio_mismatch': self._detect_carb_ratio_mismatch
        }
    
    async def analyze_patient_data(self, data: PatientData) -> List[AnalyticsResult]:
        """Run all clinical rules on patient data."""
        try:
            results = []
            
            logger.info(f"Starting analytics for patient {data.patient_id}")
            
            for rule_name, rule_function in self.rules.items():
                try:
                    result = await rule_function(data)
                    if result:
                        results.append(result)
                        logger.info(f"Rule {rule_name} found {result.count} instances")
                except Exception as e:
                    logger.error(f"Rule {rule_name} failed: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Analytics failed for patient {data.patient_id}: {e}")
            raise AnalyticsError(f"Clinical analysis failed: {e}")
    
    async def _detect_postprandial_hyperglycemia(self, data: PatientData) -> AnalyticsResult:
        """
        Detect postprandial hyperglycemia: glucose spike >180 mg/dL within 2h of meal.
        Clinical significance: Indicates need for meal insulin timing or dosing adjustment.
        """
        threshold = settings.postprandial_threshold
        window_minutes = settings.postprandial_window
        
        events = []
        meal_times = [event.timestamp for event in data.carb_events]
        
        for meal_time in meal_times:
            # Find glucose readings within postprandial window
            postprandial_readings = [
                reading for reading in data.glucose_readings
                if meal_time <= reading.timestamp <= meal_time + timedelta(minutes=window_minutes)
            ]
            
            if not postprandial_readings:
                continue
            
            # Check for spike above threshold
            max_glucose = max(reading.glucose_value for reading in postprandial_readings)
            if max_glucose > threshold:
                # Find corresponding meal for context
                meal_event = next(
                    (event for event in data.carb_events if event.timestamp == meal_time),
                    None
                )
                
                events.append({
                    'meal_time': meal_time.isoformat(),
                    'max_glucose': max_glucose,
                    'carbs': meal_event.carbs if meal_event else 'unknown',
                    'peak_time_minutes': self._find_peak_time(meal_time, postprandial_readings)
                })
        
        if not events:
            return None
        
        # Determine severity based on frequency and magnitude
        severity = self._calculate_severity(events, len(meal_times), 'postprandial')
        
        return AnalyticsResult(
            rule_name='postprandial_hyperglycemia',
            severity=severity,
            count=len(events),
            description=f"Found {len(events)} instances of postprandial hyperglycemia (>{threshold} mg/dL)",
            clinical_significance="May indicate need for meal insulin timing or dosing adjustment",
            evidence=events
        )
    
    async def _detect_mistimed_bolus(self, data: PatientData) -> AnalyticsResult:
        """
        Detect mistimed bolus: bolus >10min post-meal with glucose spike >160 mg/dL.
        Clinical significance: Suggests need for pre-meal insulin timing education.
        """
        threshold = settings.mistimed_bolus_threshold
        delay_threshold = settings.mistimed_bolus_delay
        
        events = []
        
        for carb_event in data.carb_events:
            meal_time = carb_event.timestamp
            
            # Find bolus events after meal
            delayed_boluses = [
                insulin for insulin in data.insulin_events
                if (insulin.insulin_type == 'bolus' and
                    meal_time < insulin.timestamp <= meal_time + timedelta(minutes=60) and
                    (insulin.timestamp - meal_time).total_seconds() / 60 > delay_threshold)
            ]
            
            if not delayed_boluses:
                continue
            
            # Check for glucose spike after delayed bolus
            for bolus in delayed_boluses:
                post_bolus_readings = [
                    reading for reading in data.glucose_readings
                    if bolus.timestamp <= reading.timestamp <= bolus.timestamp + timedelta(minutes=120)
                ]
                
                if not post_bolus_readings:
                    continue
                
                max_glucose = max(reading.glucose_value for reading in post_bolus_readings)
                if max_glucose > threshold:
                    delay_minutes = (bolus.timestamp - meal_time).total_seconds() / 60
                    
                    events.append({
                        'meal_time': meal_time.isoformat(),
                        'bolus_time': bolus.timestamp.isoformat(),
                        'delay_minutes': round(delay_minutes, 1),
                        'max_glucose': max_glucose,
                        'carbs': carb_event.carbs,
                        'insulin_units': bolus.units
                    })
        
        if not events:
            return None
        
        severity = self._calculate_severity(events, len(data.carb_events), 'mistimed')
        
        return AnalyticsResult(
            rule_name='mistimed_bolus',
            severity=severity,
            count=len(events),
            description=f"Found {len(events)} instances of delayed meal insulin with glucose spikes",
            clinical_significance="Suggests need for pre-meal insulin timing education",
            evidence=events
        )
    
    async def _detect_carb_ratio_mismatch(self, data: PatientData) -> AnalyticsResult:
        """
        Detect carb ratio mismatch: ≥3 similar meals with repeated hyperglycemia despite insulin.
        Clinical significance: May indicate incorrect insulin-to-carb ratio.
        """
        events = []
        
        # Group meals by similar carb content (±10g)
        meal_groups = self._group_similar_meals(data.carb_events, data.insulin_events, data.glucose_readings)
        
        for carb_range, meals in meal_groups.items():
            if len(meals) < 3:
                continue
            
            # Check for consistent hyperglycemia pattern
            hyperglycemic_meals = 0
            meal_details = []
            
            for meal in meals:
                max_glucose = meal.get('max_postprandial_glucose', 0)
                if max_glucose > settings.postprandial_threshold:
                    hyperglycemic_meals += 1
                    meal_details.append({
                        'meal_time': meal['meal_time'],
                        'carbs': meal['carbs'],
                        'insulin_units': meal['insulin_units'],
                        'max_glucose': max_glucose,
                        'estimated_ratio': round(meal['carbs'] / meal['insulin_units'], 1) if meal['insulin_units'] > 0 else None
                    })
            
            # Require at least 3 problematic meals of similar carb content
            if hyperglycemic_meals >= 3:
                events.append({
                    'carb_range': carb_range,
                    'total_meals': len(meals),
                    'problematic_meals': hyperglycemic_meals,
                    'meal_details': meal_details
                })
        
        if not events:
            return None
        
        severity = 'high' if any(event['problematic_meals'] >= 5 for event in events) else 'medium'
        
        return AnalyticsResult(
            rule_name='carb_ratio_mismatch',
            severity=severity,
            count=sum(event['problematic_meals'] for event in events),
            description=f"Found {len(events)} patterns of repeated hyperglycemia with similar meal sizes",
            clinical_significance="May indicate incorrect insulin-to-carb ratio requiring adjustment",
            evidence=events
        )
    
    def _find_peak_time(self, meal_time: datetime, readings: List[GlucoseReading]) -> int:
        """Find minutes to glucose peak after meal."""
        if not readings:
            return 0
        
        peak_reading = max(readings, key=lambda r: r.glucose_value)
        return int((peak_reading.timestamp - meal_time).total_seconds() / 60)
    
    def _calculate_severity(self, events: List[Dict], total_opportunities: int, rule_type: str) -> str:
        """Calculate severity based on frequency and context."""
        if not events or total_opportunities == 0:
            return 'low'
        
        frequency = len(events) / total_opportunities
        
        if rule_type == 'postprandial':
            if frequency >= 0.5:  # 50% of meals
                return 'high'
            elif frequency >= 0.3:  # 30% of meals
                return 'medium'
        elif rule_type == 'mistimed':
            if frequency >= 0.3:  # 30% of meals
                return 'high'
            elif frequency >= 0.2:  # 20% of meals
                return 'medium'
        
        return 'low'
    
    def _group_similar_meals(self, carb_events: List[CarbEvent], 
                           insulin_events: List[InsulinEvent], 
                           glucose_readings: List[GlucoseReading]) -> Dict[str, List[Dict]]:
        """Group meals by similar carb content for pattern analysis."""
        meal_groups = {}
        
        for carb_event in carb_events:
            meal_time = carb_event.timestamp
            
            # Find associated bolus insulin within 30 minutes before/after meal
            associated_bolus = None
            for insulin in insulin_events:
                if (insulin.insulin_type == 'bolus' and
                    abs((insulin.timestamp - meal_time).total_seconds()) <= 1800):  # 30 minutes
                    associated_bolus = insulin
                    break
            
            if not associated_bolus:
                continue
            
            # Find postprandial glucose readings
            postprandial_readings = [
                reading for reading in glucose_readings
                if meal_time <= reading.timestamp <= meal_time + timedelta(minutes=120)
            ]
            
            max_glucose = max(
                (reading.glucose_value for reading in postprandial_readings), 
                default=0
            )
            
            # Group by carb ranges (0-20g, 21-40g, 41-60g, etc.)
            carb_range = f"{int(carb_event.carbs // 20) * 20}-{int(carb_event.carbs // 20) * 20 + 19}g"
            
            if carb_range not in meal_groups:
                meal_groups[carb_range] = []
            
            meal_groups[carb_range].append({
                'meal_time': meal_time.isoformat(),
                'carbs': carb_event.carbs,
                'insulin_units': associated_bolus.units,
                'max_postprandial_glucose': max_glucose
            })
        
        return meal_groups