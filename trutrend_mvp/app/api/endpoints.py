"""FastAPI endpoint definitions."""

import logging
import statistics
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
from ..core.data_store import data_store

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
        
        # Store data and analytics results
        data_store.store_patient_data(patient_id, patient_data)
        data_store.store_analytics_results(patient_id, analytics_results)
        
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
        # Check if patient data exists
        if not data_store.has_data(patient_id):
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for patient {patient_id}. Please upload CSV data first."
            )
        
        # Get stored analytics results
        analytics_results = data_store.get_analytics_results(patient_id)
        
        if not analytics_results:
            raise HTTPException(
                status_code=404,
                detail=f"No analytics results found for patient {patient_id}"
            )
        
        return analytics_results
        
    except HTTPException:
        raise
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
    """Get analytics results for patient with user-role specific formatting."""
    try:
        # Check if patient data exists
        if not data_store.has_data(patient_id):
            raise HTTPException(
                status_code=404, 
                detail=f"No data found for patient {patient_id}. Please upload CSV data first."
            )
        
        # Get stored analytics results and patient data
        analytics_results = data_store.get_analytics_results(patient_id)
        patient_data = data_store.get_patient_data(patient_id)
        
        if not analytics_results:
            # If no analytics yet, run them now
            analytics_results = await analytics_engine.analyze_patient_data(patient_data)
            data_store.store_analytics_results(patient_id, analytics_results)
        
        # Calculate statistics from actual data
        glucose_readings = [reading.glucose_value for reading in patient_data.glucose_readings]
        if glucose_readings:
            mean_glucose = sum(glucose_readings) / len(glucose_readings)
            time_in_range = len([g for g in glucose_readings if 70 <= g <= 180]) / len(glucose_readings) * 100
            glucose_cv = (statistics.stdev(glucose_readings) / mean_glucose) * 100 if len(glucose_readings) > 1 else 0
            estimated_a1c = (mean_glucose + 46.7) / 28.7  # Approximate conversion
        else:
            mean_glucose = time_in_range = glucose_cv = estimated_a1c = 0
        
        # Generate role-specific responses based on actual analytics
        if user_role == UserRole.PATIENT:
            # Generate patient-friendly insights from actual results
            insights = []
            recommendations = []
            
            for result in analytics_results:
                if result.rule_name == "postprandial_hyperglycemia":
                    insights.append("Your glucose levels tend to rise after meals")
                    recommendations.append("Consider discussing meal insulin timing with your care team")
                elif result.rule_name == "mistimed_bolus":
                    insights.append("Taking insulin closer to meal time might help control spikes")
                    recommendations.append("Try taking insulin a few minutes before eating")
                elif result.rule_name == "carb_ratio_mismatch":
                    insights.append("Similar meals show different glucose responses")
                    recommendations.append("Keep a food diary to identify patterns")
            
            if not insights:
                insights = ["Your glucose patterns look stable"]
                recommendations = ["Continue your current diabetes management plan"]
            
            summary = f"We analyzed your diabetes data and found {len(analytics_results)} patterns worth discussing with your healthcare team." if analytics_results else "Your glucose patterns appear stable."
            
            return {
                "status": "success",
                "user_role": user_role,
                "report_type": "patient_friendly",
                "summary": summary,
                "key_insights": insights,
                "recommendations": recommendations,
                "analytics_results": analytics_results
            }
        
        else:  # Clinician role
            # Generate clinical recommendations based on actual results
            clinical_recommendations = []
            
            for result in analytics_results:
                if result.rule_name == "postprandial_hyperglycemia":
                    clinical_recommendations.append("Consider adjusting meal insulin-to-carb ratio or timing")
                elif result.rule_name == "mistimed_bolus":
                    clinical_recommendations.append("Patient education needed on pre-meal insulin timing")
                elif result.rule_name == "carb_ratio_mismatch":
                    clinical_recommendations.append("Evaluate current insulin-to-carb ratios for adjustment")
            
            if not clinical_recommendations:
                clinical_recommendations = ["Continue current management plan - patterns appear stable"]
            
            return {
                "status": "success", 
                "user_role": user_role,
                "report_type": "clinical",
                "analytics_results": analytics_results,
                "clinical_recommendations": clinical_recommendations,
                "statistical_summary": {
                    "mean_glucose": round(mean_glucose, 1),
                    "glucose_cv": round(glucose_cv, 1),
                    "time_in_range_70_180": round(time_in_range, 1),
                    "estimated_a1c": round(estimated_a1c, 1)
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics processing failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")