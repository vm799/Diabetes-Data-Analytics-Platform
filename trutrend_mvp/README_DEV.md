# TrueTrend MVP Development Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (optional, can use Docker)

### Local Development Setup

1. **Clone and Navigate**
```bash
cd trutrend_mvp
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start Services with Docker**
```bash
docker-compose up --build
```

5. **Access the Application**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

## 🏗️ Architecture Overview

### Core Modules
- **CSV Ingestion**: Auto-detects device formats, validates diabetes data
- **Analytics Engine**: Implements 3 clinical pattern detection rules
- **API Layer**: RESTful endpoints with dual-mode support
- **Data Models**: Pydantic validation for type safety

### Clinical Rules Implemented
1. **Postprandial Hyperglycemia**: Detects glucose spikes >180 mg/dL within 2h of meals
2. **Mistimed Bolus**: Identifies delayed insulin administration with subsequent spikes
3. **Carb Ratio Mismatch**: Finds repeated hyperglycemia patterns with similar meal sizes

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Files
```bash
pytest tests/test_analytics_engine.py -v
pytest tests/test_csv_ingestion.py -v
pytest tests/test_api_endpoints.py -v
```

### Test Coverage
```bash
pytest --cov=app tests/
```

## 📡 API Usage Examples

### 1. Upload CSV File
```bash
curl -X POST "http://localhost:8000/api/v1/upload-csv" \
  -F "file=@sample_diabetes_data.csv" \
  -F "patient_id=patient_001" \
  -F "user_role=clinician" \
  -F "device_type=dexcom" \
  -F "consent_confirmed=true"
```

### 2. Get Analytics Results
```bash
curl "http://localhost:8000/api/v1/analytics/patient_001?user_role=clinician"
```

### 3. Download PDF Report
```bash
curl "http://localhost:8000/api/v1/report/patient_001/pdf?user_role=patient" \
  --output patient_001_report.pdf
```

### 4. Simulate Analytics (Demo Mode)
```bash
# Patient-friendly view
curl -X POST "http://localhost:8000/api/v1/simulate-analytics/demo_patient?user_role=patient"

# Clinical view
curl -X POST "http://localhost:8000/api/v1/simulate-analytics/demo_patient?user_role=clinician"
```

## 🔧 Development Workflows

### Adding New Clinical Rules
1. Implement rule logic in `app/services/analytics_engine.py`
2. Add rule to the `rules` dictionary in `ClinicalAnalyticsEngine.__init__`
3. Create tests in `tests/test_analytics_engine.py`
4. Update configuration thresholds in `app/core/config.py`

### Supporting New Device Types
1. Add device type to `DeviceType` enum in `app/models/data_models.py`
2. Add device patterns to `CSVIngestionService.device_patterns`
3. Update column mapping logic in `_get_column_mapping`
4. Add device-specific tests

### Database Integration
Currently uses in-memory processing. To add database persistence:
1. Uncomment database models in `app/models/database.py`
2. Add database dependency injection
3. Implement data persistence in service layers

## 🚢 Deployment

### Docker Production Build
```bash
docker build -t trutrend-mvp:latest .
docker run -p 8000:8000 -e DATABASE_URL=your_db_url trutrend-mvp:latest
```

### Environment Variables
Key production variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Secure random key for encryption
- `ENCRYPTION_KEY`: 32-byte key for data encryption
- `DEBUG=false`: Disable debug mode
- `GLOOKO_API_KEY`: API key for Glooko integration

## 🔐 Security Features

### HIPAA/GDPR Compliance
- Data encryption at rest and in transit
- Audit logging for all operations
- Patient consent validation
- Data retention policies
- Role-based access control

### Security Best Practices
- Input validation on all endpoints
- Secure file upload handling
- SQL injection prevention
- XSS protection via FastAPI
- CORS configuration

## 📊 Monitoring & Observability

### Health Checks
- Application: `/api/v1/health`
- Docker: Built-in healthcheck
- Database: Connection validation

### Logging
- Structured logging with timestamps
- Audit trail for compliance
- Error tracking and debugging
- Performance monitoring

## 🔄 Next Development Phases

### Phase 2: Enhanced UI
- Web-based dashboard
- Interactive visualizations
- Real-time data streaming
- Mobile responsiveness

### Phase 3: Advanced Analytics
- Machine learning integration
- Predictive modeling
- Population health analytics
- Clinical decision support

### Phase 4: Enterprise Features
- EMR integration
- Multi-tenant architecture
- Advanced security controls
- Regulatory compliance certification

## 🤝 Contributing

### Code Style
- Follow PEP 8 guidelines
- Use type hints throughout
- Comprehensive docstrings
- Unit tests for all features

### Git Workflow
- Feature branches for development
- Pull request reviews
- Automated testing on commits
- Semantic versioning

## 📞 Support

For development questions or issues:
- Check API documentation at `/docs`
- Review test examples in `tests/`
- Consult configuration in `app/core/config.py`
- Examine service implementations in `app/services/`

---

*Built with ❤️ for the diabetes community using FastAPI, PostgreSQL, and modern Python practices.*