"""Tests for analytics engine."""

import pytest
from datetime import datetime, timedelta

from app.services.analytics_engine import ClinicalAnalyticsEngine
from app.models.data_models import PatientData, GlucoseReading, InsulinEvent, CarbEvent, DeviceType


class TestClinicalAnalyticsEngine:
    """Test clinical analytics functionality."""
    
    @pytest.fixture
    def analytics_engine(self):
        return ClinicalAnalyticsEngine()
    
    @pytest.fixture
    def sample_patient_data(self):
        """Create sample patient data for testing."""
        base_time = datetime(2024, 1, 1, 8, 0)
        
        # Create glucose readings with postprandial spikes
        glucose_readings = [
            GlucoseReading(timestamp=base_time, glucose_value=120, device_type=DeviceType.DEXCOM),
            GlucoseReading(timestamp=base_time + timedelta(minutes=30), glucose_value=200, device_type=DeviceType.DEXCOM),
            GlucoseReading(timestamp=base_time + timedelta(minutes=60), glucose_value=180, device_type=DeviceType.DEXCOM),
            GlucoseReading(timestamp=base_time + timedelta(minutes=90), glucose_value=140, device_type=DeviceType.DEXCOM),
        ]
        
        # Create carb event (meal)
        carb_events = [
            CarbEvent(timestamp=base_time, carbs=60.0, meal_type="breakfast")
        ]
        
        # Create insulin event (delayed bolus)
        insulin_events = [
            InsulinEvent(timestamp=base_time + timedelta(minutes=15), insulin_type="bolus", units=8.0)
        ]
        
        return PatientData(
            patient_id="test_patient",
            glucose_readings=glucose_readings,
            insulin_events=insulin_events,
            carb_events=carb_events,
            device_type=DeviceType.DEXCOM,
            upload_timestamp=datetime.utcnow(),
            data_start_date=base_time,
            data_end_date=base_time + timedelta(hours=2)
        )
    
    @pytest.mark.asyncio
    async def test_postprandial_hyperglycemia_detection(self, analytics_engine, sample_patient_data):
        """Test detection of postprandial hyperglycemia."""
        results = await analytics_engine.analyze_patient_data(sample_patient_data)
        
        # Should detect postprandial hyperglycemia (200 mg/dL spike)
        postprandial_results = [r for r in results if r.rule_name == "postprandial_hyperglycemia"]
        assert len(postprandial_results) == 1
        assert postprandial_results[0].count == 1
        assert postprandial_results[0].severity in ["low", "medium", "high"]
    
    @pytest.mark.asyncio
    async def test_mistimed_bolus_detection(self, analytics_engine, sample_patient_data):
        """Test detection of mistimed bolus."""
        results = await analytics_engine.analyze_patient_data(sample_patient_data)
        
        # Should detect mistimed bolus (insulin given 15 min after meal with spike)
        mistimed_results = [r for r in results if r.rule_name == "mistimed_bolus"]
        assert len(mistimed_results) == 1
        assert mistimed_results[0].count == 1
    
    @pytest.mark.asyncio
    async def test_no_patterns_detected(self, analytics_engine):
        """Test when no patterns are detected."""
        base_time = datetime(2024, 1, 1, 8, 0)
        
        # Create normal glucose readings without spikes
        glucose_readings = [
            GlucoseReading(timestamp=base_time, glucose_value=120, device_type=DeviceType.DEXCOM),
            GlucoseReading(timestamp=base_time + timedelta(minutes=30), glucose_value=125, device_type=DeviceType.DEXCOM),
            GlucoseReading(timestamp=base_time + timedelta(minutes=60), glucose_value=130, device_type=DeviceType.DEXCOM),
        ]
        
        patient_data = PatientData(
            patient_id="test_patient_normal",
            glucose_readings=glucose_readings,
            insulin_events=[],
            carb_events=[],
            device_type=DeviceType.DEXCOM,
            upload_timestamp=datetime.utcnow(),
            data_start_date=base_time,
            data_end_date=base_time + timedelta(hours=2)
        )
        
        results = await analytics_engine.analyze_patient_data(patient_data)
        
        # Should not detect any patterns
        assert len(results) == 0