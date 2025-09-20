"""Custom exception classes for the application."""

from typing import Any, Dict, Optional


class TrueTrendException(Exception):
    """Base exception class for TrueTrend application."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DataIngestionError(TrueTrendException):
    """Raised when data ingestion fails."""
    pass


class DataValidationError(TrueTrendException):
    """Raised when data validation fails."""
    pass


class AnalyticsError(TrueTrendException):
    """Raised when analytics processing fails."""
    pass


class SecurityError(TrueTrendException):
    """Raised when security validation fails."""
    pass


class ComplianceError(TrueTrendException):
    """Raised when compliance checks fail."""
    pass