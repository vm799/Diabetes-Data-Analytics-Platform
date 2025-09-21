"""Simple in-memory data store for MVP."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from ..models.data_models import PatientData, AnalyticsResult

logger = logging.getLogger(__name__)


class DataStore:
    """Simple in-memory storage for patient data and analytics results."""
    
    def __init__(self):
        self.patient_data: Dict[str, PatientData] = {}
        self.analytics_results: Dict[str, List[AnalyticsResult]] = {}
        self.upload_metadata: Dict[str, dict] = {}
    
    def store_patient_data(self, patient_id: str, data: PatientData) -> bool:
        """Store patient data."""
        try:
            self.patient_data[patient_id] = data
            self.upload_metadata[patient_id] = {
                "uploaded_at": datetime.utcnow().isoformat(),
                "data_points": len(data.glucose_readings),
                "device_type": data.device_type,
                "data_span_days": (data.data_end_date - data.data_start_date).days
            }
            logger.info(f"Stored data for patient {patient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store data for patient {patient_id}: {e}")
            return False
    
    def store_analytics_results(self, patient_id: str, results: List[AnalyticsResult]) -> bool:
        """Store analytics results for a patient."""
        try:
            self.analytics_results[patient_id] = results
            logger.info(f"Stored {len(results)} analytics results for patient {patient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store analytics for patient {patient_id}: {e}")
            return False
    
    def get_patient_data(self, patient_id: str) -> Optional[PatientData]:
        """Retrieve patient data."""
        return self.patient_data.get(patient_id)
    
    def get_analytics_results(self, patient_id: str) -> List[AnalyticsResult]:
        """Retrieve analytics results for a patient."""
        return self.analytics_results.get(patient_id, [])
    
    def get_upload_metadata(self, patient_id: str) -> Optional[dict]:
        """Get upload metadata for a patient."""
        return self.upload_metadata.get(patient_id)
    
    def has_data(self, patient_id: str) -> bool:
        """Check if data exists for patient."""
        return patient_id in self.patient_data
    
    def clear_patient_data(self, patient_id: str) -> bool:
        """Clear all data for a patient."""
        try:
            self.patient_data.pop(patient_id, None)
            self.analytics_results.pop(patient_id, None)
            self.upload_metadata.pop(patient_id, None)
            logger.info(f"Cleared data for patient {patient_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear data for patient {patient_id}: {e}")
            return False
    
    def list_patients(self) -> List[str]:
        """List all patient IDs with data."""
        return list(self.patient_data.keys())


# Global data store instance
data_store = DataStore()