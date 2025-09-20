"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO

from app.main import app
from app.models.data_models import UserRole, DeviceType


class TestAPIEndpoints:
    """Test FastAPI endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def sample_csv_content(self):
        return """timestamp,glucose_value
2024-01-01 08:00:00,120
2024-01-01 08:15:00,135
2024-01-01 08:30:00,150"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns platform information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data
        assert "TrueTrend" in data["platform"]
        assert "endpoints" in data
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_csv_upload_success(self, client, sample_csv_content):
        """Test successful CSV upload."""
        # Create a file-like object
        csv_file = BytesIO(sample_csv_content.encode())
        
        response = client.post(
            "/api/v1/upload-csv",
            files={"file": ("test.csv", csv_file, "text/csv")},
            data={
                "patient_id": "test_patient_001",
                "user_role": UserRole.CLINICIAN,
                "device_type": DeviceType.DEXCOM,
                "consent_confirmed": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["patient_id"] == "test_patient_001"
        assert "analytics_found" in data
    
    def test_csv_upload_no_consent(self, client, sample_csv_content):
        """Test CSV upload without consent fails."""
        csv_file = BytesIO(sample_csv_content.encode())
        
        response = client.post(
            "/api/v1/upload-csv",
            files={"file": ("test.csv", csv_file, "text/csv")},
            data={
                "patient_id": "test_patient_001",
                "user_role": UserRole.PATIENT,
                "consent_confirmed": False
            }
        )
        
        assert response.status_code == 400
        assert "consent" in response.json()["detail"].lower()
    
    def test_csv_upload_invalid_file_type(self, client):
        """Test CSV upload with invalid file type fails."""
        txt_file = BytesIO(b"not a csv file")
        
        response = client.post(
            "/api/v1/upload-csv",
            files={"file": ("test.txt", txt_file, "text/plain")},
            data={
                "patient_id": "test_patient_001",
                "user_role": UserRole.CLINICIAN,
                "consent_confirmed": True
            }
        )
        
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]
    
    def test_get_analytics_results(self, client):
        """Test getting analytics results."""
        response = client.get(
            "/api/v1/analytics/test_patient_001",
            params={"user_role": UserRole.CLINICIAN}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_download_pdf_report(self, client):
        """Test PDF report download."""
        response = client.get(
            "/api/v1/report/test_patient_001/pdf",
            params={"user_role": UserRole.CLINICIAN}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
    
    def test_simulate_analytics_patient_mode(self, client):
        """Test analytics simulation in patient mode."""
        response = client.post(
            "/api/v1/simulate-analytics/test_patient_001",
            params={"user_role": UserRole.PATIENT}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user_role"] == UserRole.PATIENT
        assert data["report_type"] == "patient_friendly"
        assert "summary" in data
        assert "key_insights" in data
        assert "recommendations" in data
    
    def test_simulate_analytics_clinician_mode(self, client):
        """Test analytics simulation in clinician mode."""
        response = client.post(
            "/api/v1/simulate-analytics/test_patient_001",
            params={"user_role": UserRole.CLINICIAN}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user_role"] == UserRole.CLINICIAN
        assert data["report_type"] == "clinical"
        assert "clinical_recommendations" in data
        assert "statistical_summary" in data
    
    def test_404_endpoint(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404