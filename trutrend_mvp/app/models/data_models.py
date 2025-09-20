"""Pydantic models for data validation and serialization."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DeviceType(str, Enum):
    """Supported diabetes device types."""
    DEXCOM = "dexcom"
    LIBREVIEW = "libreview"
    TANDEM = "tandem"
    MEDTRONIC = "medtronic"
    GLOOKO = "glooko"
    UNKNOWN = "unknown"


class UserRole(str, Enum):
    """User roles for dual-mode interface."""
    CLINICIAN = "clinician"
    PATIENT = "patient"


class GlucoseReading(BaseModel):
    """Standard glucose reading model."""
    timestamp: datetime
    glucose_value: float = Field(..., ge=20, le=600, description="Glucose value in mg/dL")
    device_type: DeviceType
    trend_arrow: Optional[str] = None
    
    @validator('glucose_value')
    def validate_glucose_range(cls, v):
        if v < 20 or v > 600:
            raise ValueError('Glucose value must be between 20-600 mg/dL')
        return v


class InsulinEvent(BaseModel):
    """Insulin administration event."""
    timestamp: datetime
    insulin_type: str = Field(..., description="bolus or basal")
    units: float = Field(..., ge=0, le=100, description="Insulin units")
    
    @validator('insulin_type')
    def validate_insulin_type(cls, v):
        if v.lower() not in ['bolus', 'basal']:
            raise ValueError('Insulin type must be bolus or basal')
        return v.lower()


class CarbEvent(BaseModel):
    """Carbohydrate intake event."""
    timestamp: datetime
    carbs: float = Field(..., ge=0, le=500, description="Carbohydrate grams")
    meal_type: Optional[str] = None


class PatientData(BaseModel):
    """Complete patient diabetes data."""
    patient_id: str
    glucose_readings: List[GlucoseReading]
    insulin_events: List[InsulinEvent]
    carb_events: List[CarbEvent]
    device_type: DeviceType
    upload_timestamp: datetime
    data_start_date: datetime
    data_end_date: datetime


class AnalyticsResult(BaseModel):
    """Clinical analytics result."""
    rule_name: str
    severity: str = Field(..., description="low, medium, high")
    count: int
    description: str
    clinical_significance: str
    evidence: List[Dict[str, Any]]
    
    @validator('severity')
    def validate_severity(cls, v):
        if v.lower() not in ['low', 'medium', 'high']:
            raise ValueError('Severity must be low, medium, or high')
        return v.lower()


class PatientReport(BaseModel):
    """Patient-friendly report."""
    patient_id: str
    generated_at: datetime
    summary: str
    key_insights: List[str]
    recommendations: List[str]
    analytics_results: List[AnalyticsResult]
    disclaimer: str = "Please discuss these insights with your healthcare provider."


class ClinicalReport(BaseModel):
    """Clinical report with technical details."""
    patient_id: str
    generated_at: datetime
    analytics_results: List[AnalyticsResult]
    statistical_summary: Dict[str, Any]
    clinical_recommendations: List[str]
    data_quality_metrics: Dict[str, Any]


class CSVUploadRequest(BaseModel):
    """CSV file upload request."""
    patient_id: str
    device_type: Optional[DeviceType] = DeviceType.UNKNOWN
    user_role: UserRole
    consent_confirmed: bool = Field(..., description="Patient consent confirmation")
    
    @validator('consent_confirmed')
    def validate_consent(cls, v):
        if not v:
            raise ValueError('Patient consent must be confirmed')
        return v