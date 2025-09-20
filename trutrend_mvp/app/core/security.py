"""Security and compliance utilities for HIPAA/GDPR."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet

from .config import settings

logger = logging.getLogger(__name__)


class SecurityManager:
    """Handles encryption, audit logging, and compliance requirements."""
    
    def __init__(self):
        # For MVP, use a simple key - in production, use proper key management
        key = Fernet.generate_key()
        self.cipher_suite = Fernet(key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive patient data."""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive patient data."""
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def hash_patient_id(self, patient_id: str) -> str:
        """Create consistent hash for patient identification."""
        return hashlib.sha256(f"{patient_id}{settings.secret_key}".encode()).hexdigest()
    
    def log_audit_event(self, event_type: str, user_id: str, 
                       patient_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Log audit events for compliance."""
        if not settings.audit_logging:
            return
        
        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "patient_id": self.hash_patient_id(patient_id) if patient_id else None,
            "details": details or {}
        }
        
        # In production, this would go to a secure audit database
        logger.info(f"AUDIT: {audit_record}")
    
    def check_data_retention(self, created_date: datetime) -> bool:
        """Check if data is within retention period."""
        retention_limit = datetime.utcnow() - timedelta(days=settings.data_retention_days)
        return created_date > retention_limit
    
    def validate_consent(self, patient_id: str, data_type: str) -> bool:
        """Validate patient consent for data processing."""
        # Stub implementation - in production, check consent database
        logger.info(f"Validating consent for patient {self.hash_patient_id(patient_id)} for {data_type}")
        return True


security_manager = SecurityManager()