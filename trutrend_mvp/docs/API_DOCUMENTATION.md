# TrueTrend Diabetes Analytics Platform - API Documentation

## Overview

The TrueTrend API provides a comprehensive diabetes analytics platform with CSV data ingestion, clinical pattern detection, and dual-mode reporting for both healthcare providers and patients. The API is built with FastAPI and follows RESTful principles with comprehensive input validation and security features.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: `https://api.trutrend.health`

## Authentication

Currently implemented as MVP without authentication. Production deployment should implement:
- JWT-based authentication
- Role-based access control (RBAC)
- OAuth 2.0 integration with healthcare systems

## API Versioning

All endpoints are versioned under `/api/v1/`

## Content Types

- **Request**: `application/json`, `multipart/form-data` (for file uploads)
- **Response**: `application/json`, `application/pdf` (for reports)

---

## Endpoints

### Platform Information

#### GET `/`
**Description**: Get platform information and available endpoints

**Parameters**: None

**Response**:
```json
{
  "platform": "TrueTrend Diabetes Analytics",
  "version": "1.0.0-MVP",
  "description": "Honest clinical diabetes insights",
  "status": "operational",
  "features": [
    "CSV data ingestion (Dexcom, LibreView, Glooko, etc.)",
    "Clinical pattern detection",
    "Dual-mode reporting (clinical/patient)",
    "HIPAA/GDPR compliance framework",
    "Real-time analytics processing"
  ],
  "endpoints": {
    "upload": "/api/v1/upload-csv",
    "analytics": "/api/v1/analytics/{patient_id}",
    "reports": "/api/v1/report/{patient_id}/pdf",
    "simulate": "/api/v1/simulate-analytics/{patient_id}",
    "health": "/api/v1/health"
  },
  "demo_instructions": {
    "step_1": "Upload a CSV file using POST /api/v1/upload-csv",
    "step_2": "View analytics using GET /api/v1/analytics/{patient_id}",
    "step_3": "Try simulation mode: POST /api/v1/simulate-analytics/{patient_id}",
    "documentation": "Visit /docs for interactive API documentation"
  }
}
```

---

### Health Check

#### GET `/api/v1/health`
**Description**: Check system health and status

**Parameters**: None

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "1.0.0-MVP",
  "service": "TrueTrend Diabetes Analytics Platform"
}
```

**Status Codes**:
- `200 OK`: System is healthy
- `503 Service Unavailable`: System is unhealthy

---

### Data Upload

#### POST `/api/v1/upload-csv`
**Description**: Upload and process diabetes data from CSV files

**Content-Type**: `multipart/form-data`

**Parameters**:
- `file` (file, required): CSV file containing diabetes data
- `patient_id` (string, required): Unique patient identifier
- `user_role` (enum, required): `clinician` or `patient`
- `device_type` (enum, optional): Device type - `dexcom`, `libreview`, `tandem`, `medtronic`, `glooko`, `unknown`
- `consent_confirmed` (boolean, required): Patient consent confirmation

**Supported CSV Formats**:

**Dexcom Format**:
```csv
timestamp,glucose_value,trend_arrow
2024-01-01 08:00:00,120,→
2024-01-01 08:15:00,135,↗
2024-01-01 08:30:00,150,↗
```

**LibreView Format**:
```csv
time,historic_glucose,notes
01/01/2024 08:00,120,before_meal
01/01/2024 08:15,135,
01/01/2024 08:30,150,after_meal
```

**Glooko/Comprehensive Format**:
```csv
timestamp,bg_value,bolus_insulin,basal_insulin,carbohydrates,meal_type
2024-01-01 08:00:00,120,0,1.2,45,breakfast
2024-01-01 08:15:00,135,6,1.2,0,
2024-01-01 08:30:00,150,0,1.2,0,
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/upload-csv" \
  -F "file=@diabetes_data.csv" \
  -F "patient_id=patient_001" \
  -F "user_role=clinician" \
  -F "device_type=dexcom" \
  -F "consent_confirmed=true"
```

**Response**:
```json
{
  "status": "success",
  "message": "Processed 288 glucose readings",
  "analytics_found": 3,
  "report_generated": true,
  "patient_id": "patient_001",
  "device_type": "dexcom",
  "data_span_days": 14
}
```

**Error Responses**:
```json
{
  "detail": "Patient consent required"
}
```

**Status Codes**:
- `200 OK`: Upload successful
- `400 Bad Request`: Invalid file type, missing consent, or data validation error
- `422 Unprocessable Entity`: Data format issues
- `500 Internal Server Error`: Processing error

---

### Analytics Results

#### GET `/api/v1/analytics/{patient_id}`
**Description**: Retrieve analytics results for a patient

**Parameters**:
- `patient_id` (path, required): Patient identifier
- `user_role` (query, required): `clinician` or `patient`

**Example Request**:
```bash
curl "http://localhost:8000/api/v1/analytics/patient_001?user_role=clinician"
```

**Response**:
```json
[
  {
    "rule_name": "postprandial_hyperglycemia",
    "severity": "medium",
    "count": 5,
    "description": "Found 5 instances of postprandial hyperglycemia (>180 mg/dL)",
    "clinical_significance": "May indicate need for meal insulin timing or dosing adjustment",
    "evidence": [
      {
        "meal_time": "2024-01-01T08:00:00",
        "max_glucose": 210,
        "carbs": 45,
        "peak_time_minutes": 75
      },
      {
        "meal_time": "2024-01-01T12:30:00",
        "max_glucose": 195,
        "carbs": 30,
        "peak_time_minutes": 60
      }
    ]
  },
  {
    "rule_name": "mistimed_bolus",
    "severity": "low",
    "count": 2,
    "description": "Found 2 instances of delayed meal insulin with glucose spikes",
    "clinical_significance": "Suggests need for pre-meal insulin timing education",
    "evidence": [
      {
        "meal_time": "2024-01-01T18:00:00",
        "bolus_time": "2024-01-01T18:15:00",
        "delay_minutes": 15,
        "max_glucose": 185,
        "carbs": 50,
        "insulin_units": 6
      }
    ]
  }
]
```

**Status Codes**:
- `200 OK`: Analytics retrieved successfully
- `404 Not Found`: Patient not found
- `500 Internal Server Error`: Analytics processing error

---

### PDF Reports

#### GET `/api/v1/report/{patient_id}/pdf`
**Description**: Generate and download PDF report

**Parameters**:
- `patient_id` (path, required): Patient identifier
- `user_role` (query, required): `clinician` or `patient`

**Example Request**:
```bash
curl "http://localhost:8000/api/v1/report/patient_001/pdf?user_role=patient" \
  --output patient_001_report.pdf
```

**Response**: PDF file download

**Headers**:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename=patient_001_report.pdf
```

**Status Codes**:
- `200 OK`: PDF generated successfully
- `404 Not Found`: Patient not found
- `500 Internal Server Error`: PDF generation error

---

### Analytics Simulation

#### POST `/api/v1/simulate-analytics/{patient_id}`
**Description**: Simulate analytics processing for demonstration purposes

**Parameters**:
- `patient_id` (path, required): Patient identifier
- `user_role` (query, required): `clinician` or `patient`

**Example Request**:
```bash
# Patient Mode
curl -X POST "http://localhost:8000/api/v1/simulate-analytics/demo_patient?user_role=patient"

# Clinician Mode
curl -X POST "http://localhost:8000/api/v1/simulate-analytics/demo_patient?user_role=clinician"
```

**Patient Mode Response**:
```json
{
  "status": "success",
  "user_role": "patient",
  "report_type": "patient_friendly",
  "summary": "We analyzed your recent diabetes data and found some patterns worth discussing with your healthcare team.",
  "key_insights": [
    "Glucose levels tend to rise after meals, particularly dinner",
    "Taking insulin a few minutes before eating might help control spikes"
  ],
  "recommendations": [
    "Consider discussing meal insulin timing with your care team",
    "Keep a food diary to identify which meals cause the highest glucose rises",
    "Continue regular glucose monitoring as prescribed"
  ],
  "analytics_results": [
    {
      "rule_name": "postprandial_hyperglycemia",
      "severity": "high",
      "count": 5,
      "description": "Found 5 instances of postprandial hyperglycemia (>180 mg/dL)",
      "clinical_significance": "Indicates need for meal insulin timing or dosing adjustment",
      "evidence": [...]
    }
  ]
}
```

**Clinician Mode Response**:
```json
{
  "status": "success",
  "user_role": "clinician",
  "report_type": "clinical",
  "analytics_results": [
    {
      "rule_name": "postprandial_hyperglycemia",
      "severity": "high",
      "count": 5,
      "description": "Found 5 instances of postprandial hyperglycemia (>180 mg/dL)",
      "clinical_significance": "Indicates need for meal insulin timing or dosing adjustment",
      "evidence": [...]
    }
  ],
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
```

**Status Codes**:
- `200 OK`: Simulation completed successfully
- `500 Internal Server Error`: Simulation error

---

## Clinical Analytics Rules

The platform implements three primary clinical pattern detection rules:

### 1. Postprandial Hyperglycemia
**Definition**: Glucose spike >180 mg/dL within 2 hours of meal
**Clinical Significance**: May indicate need for meal insulin timing or dosing adjustment
**Severity Levels**:
- High: ≥50% of meals affected
- Medium: 30-49% of meals affected  
- Low: <30% of meals affected

### 2. Mistimed Bolus
**Definition**: Bolus >10 minutes post-meal with glucose spike >160 mg/dL
**Clinical Significance**: Suggests need for pre-meal insulin timing education
**Severity Levels**:
- High: ≥30% of meals affected
- Medium: 20-29% of meals affected
- Low: <20% of meals affected

### 3. Carb Ratio Mismatch
**Definition**: ≥3 similar meals with repeated hyperglycemia despite insulin
**Clinical Significance**: May indicate incorrect insulin-to-carb ratio
**Severity Levels**:
- High: ≥5 problematic meals in same carb range
- Medium: 3-4 problematic meals in same carb range

---

## Data Models

### Glucose Reading
```json
{
  "timestamp": "2024-01-01T08:00:00",
  "glucose_value": 120.0,
  "device_type": "dexcom",
  "trend_arrow": "→"
}
```

### Insulin Event
```json
{
  "timestamp": "2024-01-01T08:00:00",
  "insulin_type": "bolus",
  "units": 6.0
}
```

### Carb Event
```json
{
  "timestamp": "2024-01-01T08:00:00",
  "carbs": 45.0,
  "meal_type": "breakfast"
}
```

### Analytics Result
```json
{
  "rule_name": "postprandial_hyperglycemia",
  "severity": "medium",
  "count": 5,
  "description": "Found 5 instances of postprandial hyperglycemia (>180 mg/dL)",
  "clinical_significance": "May indicate need for meal insulin timing or dosing adjustment",
  "evidence": [...]
}
```

---

## Error Handling

### Standard Error Response Format
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Common Error Codes
- `CONSENT_REQUIRED`: Patient consent not provided
- `INVALID_FILE_TYPE`: File is not a valid CSV
- `DATA_VALIDATION_ERROR`: CSV data format issues
- `PATIENT_NOT_FOUND`: Patient ID not found
- `ANALYTICS_PROCESSING_ERROR`: Error during analytics processing
- `INSUFFICIENT_DATA`: Not enough data for meaningful analysis

---

## Rate Limiting

- **Upload endpoints**: 10 requests per minute per IP
- **Analytics endpoints**: 100 requests per minute per IP
- **Report generation**: 5 requests per minute per IP

---

## HIPAA/GDPR Compliance

### Data Encryption
- All data encrypted at rest using AES-256
- Transport encryption via TLS 1.3
- Patient IDs hashed for logging

### Audit Logging
All operations are logged with:
- Timestamp
- User role and action
- Patient ID (hashed)
- Operation details
- IP address (for security)

### Data Retention
- Patient data: 7 years (configurable)
- Audit logs: 10 years
- Analytics results: 2 years

### Consent Management
- Explicit consent required for all data processing
- Consent withdrawal supported
- Data deletion upon request

---

## Interactive Documentation

Visit `/docs` for Swagger/OpenAPI interactive documentation where you can:
- Test all endpoints directly
- View detailed request/response schemas
- Generate code examples in multiple languages
- Download OpenAPI specification

---

## SDK and Integration Examples

### Python SDK Example
```python
import requests
import json

# Upload CSV file
def upload_diabetes_data(file_path, patient_id):
    url = "http://localhost:8000/api/v1/upload-csv"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'patient_id': patient_id,
            'user_role': 'clinician',
            'device_type': 'dexcom',
            'consent_confirmed': True
        }
        
        response = requests.post(url, files=files, data=data)
        return response.json()

# Get analytics results
def get_analytics(patient_id, user_role='clinician'):
    url = f"http://localhost:8000/api/v1/analytics/{patient_id}"
    params = {'user_role': user_role}
    
    response = requests.get(url, params=params)
    return response.json()

# Example usage
result = upload_diabetes_data('patient_data.csv', 'patient_001')
analytics = get_analytics('patient_001')
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// Upload CSV file
async function uploadDiabetesData(filePath, patientId) {
    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    form.append('patient_id', patientId);
    form.append('user_role', 'clinician');
    form.append('device_type', 'dexcom');
    form.append('consent_confirmed', true);
    
    try {
        const response = await axios.post(
            'http://localhost:8000/api/v1/upload-csv',
            form,
            { headers: form.getHeaders() }
        );
        return response.data;
    } catch (error) {
        console.error('Upload failed:', error.response.data);
        throw error;
    }
}

// Get analytics results
async function getAnalytics(patientId, userRole = 'clinician') {
    try {
        const response = await axios.get(
            `http://localhost:8000/api/v1/analytics/${patientId}`,
            { params: { user_role: userRole } }
        );
        return response.data;
    } catch (error) {
        console.error('Analytics fetch failed:', error.response.data);
        throw error;
    }
}

// Example usage
(async () => {
    try {
        const result = await uploadDiabetesData('patient_data.csv', 'patient_001');
        console.log('Upload result:', result);
        
        const analytics = await getAnalytics('patient_001');
        console.log('Analytics:', analytics);
    } catch (error) {
        console.error('Error:', error);
    }
})();
```

---

## Support and Resources

- **Interactive Documentation**: `/docs`
- **Health Check**: `/api/v1/health`
- **Platform Information**: `/`
- **GitHub Repository**: [Link to repository]
- **Support Email**: support@trutrend.health
- **Status Page**: https://status.trutrend.health