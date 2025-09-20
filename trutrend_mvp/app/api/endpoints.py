"""FastAPI endpoint definitions."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response

from ..models.data_models import (
    CSVUploadRequest, PatientReport, ClinicalReport, 
    UserRole, DeviceType, AnalyticsResult
)
from ..services.csv_ingestion import CSVIngestionService
from ..services.analytics_engine import ClinicalAnalyticsEngine
from ..core.exceptions import DataIngestionError, DataValidationError, AnalyticsError

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
csv_service = CSVIngestionService()
analytics_engine = ClinicalAnalyticsEngine()


@router.post("/upload-csv", response_model=dict)
async def upload_csv_file(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    user_role: UserRole = Form(...),
    device_type: Optional[DeviceType] = Form(DeviceType.UNKNOWN),
    consent_confirmed: bool = Form(...)
):
    """Upload and process CSV file with diabetes data."""
    try:
        # Validate consent
        if not consent_confirmed:
            raise HTTPException(status_code=400, detail="Patient consent required")
        
        # Validate file
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Process CSV
        patient_data = await csv_service.process_csv_file(
            file_content, patient_id, device_type
        )
        
        # Run analytics
        analytics_results = await analytics_engine.analyze_patient_data(patient_data)
        
        return {
            "status": "success",
            "message": f"Processed {len(patient_data.glucose_readings)} glucose readings",
            "analytics_found": len(analytics_results),
            "report_generated": True,
            "patient_id": patient_id,
            "device_type": patient_data.device_type,
            "data_span_days": (patient_data.data_end_date - patient_data.data_start_date).days
        }
        
    except DataIngestionError as e:
        logger.error(f"CSV ingestion failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DataValidationError as e:
        logger.error(f"Data validation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except AnalyticsError as e:
        logger.error(f"Analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in CSV upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/{patient_id}", response_model=List[AnalyticsResult])
async def get_analytics_results(
    patient_id: str,
    user_role: UserRole
):
    """Get analytics results for a patient."""
    try:
        # In production, this would fetch from database
        # For MVP, return placeholder analytics results
        sample_results = [
            AnalyticsResult(
                rule_name="postprandial_hyperglycemia",
                severity="medium",
                count=3,
                description="Found 3 instances of postprandial hyperglycemia (>180 mg/dL)",
                clinical_significance="May indicate need for meal insulin timing or dosing adjustment",
                evidence=[
                    {
                        "meal_time": "2024-01-01T08:00:00",
                        "max_glucose": 210,
                        "carbs": 45,
                        "peak_time_minutes": 75
                    }
                ]
            )
        ]
        
        return sample_results
        
    except Exception as e:
        logger.error(f"Failed to get analytics results: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/report/{patient_id}/pdf")
async def download_pdf_report(
    patient_id: str,
    user_role: UserRole
):
    """Download PDF report for patient."""
    try:
        # In production, this would generate actual PDF
        # For MVP, return placeholder response
        pdf_content = b"PDF report placeholder content for TrueTrend analytics"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={patient_id}_report.pdf"}
        )
        
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-MVP",
        "service": "TrueTrend Diabetes Analytics Platform"
    }


@router.post("/simulate-analytics/{patient_id}")
async def simulate_analytics(
    patient_id: str,
    user_role: UserRole
):
    """Simulate analytics processing for demonstration."""
    try:
        # Simulate analytics results for demo
        demo_results = [
            AnalyticsResult(
                rule_name="postprandial_hyperglycemia",
                severity="high",
                count=5,
                description="Found 5 instances of postprandial hyperglycemia (>180 mg/dL)",
                clinical_significance="Indicates need for meal insulin timing or dosing adjustment",
                evidence=[
                    {
                        "meal_time": "2024-01-01T08:00:00",
                        "max_glucose": 220,
                        "carbs": 60,
                        "peak_time_minutes": 90
                    },
                    {
                        "meal_time": "2024-01-01T12:30:00", 
                        "max_glucose": 195,
                        "carbs": 45,
                        "peak_time_minutes": 60
                    }
                ]
            ),
            AnalyticsResult(
                rule_name="mistimed_bolus",
                severity="medium",
                count=2,
                description="Found 2 instances of delayed meal insulin with glucose spikes",
                clinical_significance="Suggests need for pre-meal insulin timing education",
                evidence=[
                    {
                        "meal_time": "2024-01-01T18:00:00",
                        "bolus_time": "2024-01-01T18:15:00",
                        "delay_minutes": 15,
                        "max_glucose": 185,
                        "carbs": 50,
                        "insulin_units": 6
                    }
                ]
            )
        ]
        
        # Generate different reports based on user role
        if user_role == UserRole.PATIENT:
            summary = "We analyzed your recent diabetes data and found some patterns worth discussing with your healthcare team."
            insights = [
                "Glucose levels tend to rise after meals, particularly dinner",
                "Taking insulin a few minutes before eating might help control spikes"
            ]
            recommendations = [
                "Consider discussing meal insulin timing with your care team",
                "Keep a food diary to identify which meals cause the highest glucose rises",
                "Continue regular glucose monitoring as prescribed"
            ]
            
            return {
                "status": "success",
                "user_role": user_role,
                "report_type": "patient_friendly",
                "summary": summary,
                "key_insights": insights,
                "recommendations": recommendations,
                "analytics_results": demo_results
            }
        
        else:  # Clinician role
            return {
                "status": "success", 
                "user_role": user_role,
                "report_type": "clinical",
                "analytics_results": demo_results,
                "clinical_recommendations": [
                    "Consider adjusting meal insulin-to-carb ratio or timing",
                    "Patient education needed on pre-meal insulin timing",
                    "Evaluate current insulin type and absorption profile"
                ],
                "statistical_summary": {
                    "mean_glucose": 145.2,
                    "glucose_cv": 28.5,
                    "time_in_range_70_180": 68.4,
                    "estimated_a1c": 7.2
                }
            }
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")