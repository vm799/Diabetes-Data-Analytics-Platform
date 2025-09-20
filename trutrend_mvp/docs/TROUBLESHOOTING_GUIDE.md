# TrueTrend Diabetes Analytics Platform - Troubleshooting Guide

## Overview

This comprehensive troubleshooting guide helps resolve common issues with the TrueTrend Diabetes Analytics Platform. It covers problems from basic connectivity issues to complex data processing errors, with step-by-step solutions for users, developers, and system administrators.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common User Issues](#common-user-issues)
3. [Data Upload Problems](#data-upload-problems)
4. [Analytics and Processing Issues](#analytics-and-processing-issues)
5. [System Administration Issues](#system-administration-issues)
6. [Performance Issues](#performance-issues)
7. [Security and Access Issues](#security-and-access-issues)
8. [Integration Problems](#integration-problems)
9. [Emergency Procedures](#emergency-procedures)
10. [Getting Support](#getting-support)

---

## Quick Diagnostics

### System Health Check

#### Step 1: Verify Platform Status
```bash
# Check platform health
curl https://your-domain.com/api/v1/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "1.0.0-MVP",
  "service": "TrueTrend Diabetes Analytics Platform"
}
```

#### Step 2: Check Component Status
```bash
# Database connectivity
curl https://your-domain.com/api/v1/health | jq '.database_status'

# API responsiveness
time curl https://your-domain.com/api/v1/health

# Service dependencies
docker-compose ps  # For Docker deployments
```

#### Step 3: Review Recent Logs
```bash
# Application logs
docker-compose logs trutrend-api --tail=50

# Error patterns
docker-compose logs trutrend-api | grep ERROR

# Performance issues
docker-compose logs trutrend-api | grep "slow\|timeout\|performance"
```

### Quick Problem Identification

| Symptom | Likely Cause | Quick Check |
|---------|--------------|-------------|
| **Platform won't load** | Network/Server issue | `curl https://your-domain.com/api/v1/health` |
| **Upload fails** | File format/Size issue | Check file is CSV <50MB |
| **No analytics results** | Insufficient data | Verify >10 glucose readings |
| **Slow response** | Performance issue | Check server resources |
| **Access denied** | Authentication issue | Verify user permissions |

---

## Common User Issues

### Issue 1: Cannot Access Platform

#### Symptoms
- Website won't load
- "Connection refused" errors
- Timeout errors

#### Diagnosis Steps
```bash
# Test basic connectivity
ping your-domain.com

# Test HTTPS access
curl -I https://your-domain.com

# Check DNS resolution
nslookup your-domain.com
```

#### Solutions

**Solution A: Network Issues**
1. Check internet connection
2. Try different network (mobile data)
3. Disable VPN if using one
4. Clear browser cache and cookies

**Solution B: Browser Issues**
1. Try different browser
2. Disable browser extensions
3. Clear DNS cache:
   ```bash
   # Windows
   ipconfig /flushdns
   
   # macOS
   sudo dscacheutil -flushcache
   
   # Linux
   sudo systemctl flush-dns
   ```

**Solution C: Platform Downtime**
1. Check status page: https://status.trutrend.health
2. Contact support if extended outage
3. Try again in a few minutes

### Issue 2: Login/Authentication Problems

#### Symptoms
- Cannot log in with correct credentials
- Session expires quickly
- "Unauthorized" error messages

#### Solutions

**For Current MVP (No Authentication)**
- Platform currently operates without user authentication
- Access should be available to all users
- If seeing authentication errors, contact support

**For Future Authentication System**
```bash
# Reset user session
curl -X POST https://your-domain.com/api/v1/auth/logout

# Verify user permissions
curl https://your-domain.com/api/v1/auth/verify-token \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Issue 3: Mobile Access Issues

#### Symptoms
- Interface doesn't display properly on phone/tablet
- Touch interactions don't work
- File upload fails on mobile

#### Solutions
1. **Use recommended browsers**: Chrome, Safari, Firefox
2. **Enable JavaScript**: Required for platform functionality
3. **Check mobile data limits**: Large file uploads need sufficient data
4. **Try landscape mode**: Better display for complex interfaces
5. **Use desktop for large uploads**: More reliable for big files

---

## Data Upload Problems

### Issue 1: CSV File Upload Fails

#### Symptoms
- "Only CSV files are supported" error
- File upload button doesn't work
- Upload progress stalls

#### Diagnosis
```bash
# Check file format
file your_data.csv
# Should show: ASCII text, with CRLF line terminators

# Check file size
ls -lh your_data.csv
# Should be under 50MB

# Validate CSV structure
head -5 your_data.csv
```

#### Solutions

**Solution A: File Format Issues**
```bash
# Convert to proper CSV format
# From Excel: Save As > CSV (Comma delimited)
# From Google Sheets: File > Download > CSV

# Fix line endings (if needed)
dos2unix your_data.csv  # Linux/Mac
```

**Solution B: File Size Issues**
```bash
# Check file size
ls -lh your_data.csv

# If too large, split the file
split -l 1000 your_data.csv smaller_file_
# Upload smaller files separately
```

**Solution C: Content Issues**
```bash
# Remove special characters
sed 's/[^\x00-\x7F]//g' your_data.csv > clean_data.csv

# Check for required columns
head -1 your_data.csv | tr ',' '\n' | nl
```

### Issue 2: Device Data Export Problems

#### Dexcom Clarity Export Issues

**Problem**: Cannot export data from Dexcom Clarity
**Solutions**:
1. **Log into Clarity website**: https://clarity.dexcom.com
2. **Select correct date range**: Minimum 7 days recommended
3. **Choose "Export Data"**: Select all available data types
4. **Save as CSV**: Not Excel or PDF format

```bash
# Validate Dexcom CSV format
head -3 dexcom_export.csv
# Expected format:
# timestamp,glucose_value,trend_arrow
# 2024-01-01 08:00:00,120,→
```

#### LibreView Export Issues

**Problem**: LibreView export doesn't include all data
**Solutions**:
1. **Use LibreView website**: Not the mobile app
2. **Select "Download Report"**: Choose comprehensive report
3. **Export as CSV**: Select comma-separated values
4. **Include glucose history**: Ensure historical data is selected

```bash
# Validate LibreView CSV format
head -3 libreview_export.csv
# Expected format:
# time,historic_glucose,notes
# 01/01/2024 08:00,120,before_meal
```

#### Glooko Export Issues

**Problem**: Glooko export missing insulin/carb data
**Solutions**:
1. **Use Glooko website**: https://my.glooko.com
2. **Select "Export"**: Choose comprehensive export
3. **Include all data types**: Glucose, insulin, carbs, notes
4. **Select CSV format**: Not PDF report

### Issue 3: Data Validation Errors

#### Symptoms
- "Data validation failed" errors
- "No valid glucose readings found"
- Processing fails after upload

#### Common Validation Issues

**Invalid Glucose Values**
```bash
# Check for out-of-range values
awk -F',' '$2 < 20 || $2 > 600 {print NR, $0}' your_data.csv
# Glucose values must be 20-600 mg/dL
```

**Missing Timestamps**
```bash
# Check for empty timestamp fields
awk -F',' '$1 == "" {print "Empty timestamp at line " NR}' your_data.csv
```

**Invalid Date Formats**
```bash
# Common date format issues
grep -n "[0-9][0-9]/[0-9][0-9]/[0-9][0-9]" your_data.csv
# Should be: YYYY-MM-DD HH:MM:SS or MM/DD/YYYY HH:MM
```

#### Solutions

**Fix Glucose Values**
```python
# Python script to clean glucose data
import pandas as pd

df = pd.read_csv('your_data.csv')
# Remove invalid glucose values
df = df[(df['glucose_value'] >= 20) & (df['glucose_value'] <= 600)]
df.to_csv('cleaned_data.csv', index=False)
```

**Fix Date Formats**
```python
# Standardize date formats
import pandas as pd
from datetime import datetime

df = pd.read_csv('your_data.csv')
# Convert various date formats to standard
df['timestamp'] = pd.to_datetime(df['timestamp'], infer_datetime_format=True)
df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
df.to_csv('fixed_dates.csv', index=False)
```

---

## Analytics and Processing Issues

### Issue 1: No Analytics Results Generated

#### Symptoms
- Empty analytics results array
- "No patterns found" message
- Processing completes but no insights

#### Diagnosis Steps
```bash
# Check data sufficiency
curl "https://your-domain.com/api/v1/analytics/PATIENT_ID?user_role=clinician"

# Review upload results
# Look for: "analytics_found": 0
```

#### Common Causes and Solutions

**Insufficient Data Volume**
- **Requirement**: Minimum 10 glucose readings
- **Recommendation**: 14+ days of data for comprehensive analysis
- **Solution**: Upload more data covering longer time period

**No Meal/Insulin Data**
- **Pattern detection** requires meal timing or insulin data
- **Solution**: Export comprehensive data including insulin and carbs
- **Alternative**: Use simulation mode for demonstration

**Data Quality Issues**
```python
# Check data quality
import pandas as pd

df = pd.read_csv('your_data.csv')
print(f"Total readings: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Glucose range: {df['glucose_value'].min()} to {df['glucose_value'].max()}")

# Check for meal patterns
if 'carbohydrates' in df.columns:
    meals = df[df['carbohydrates'] > 0]
    print(f"Meals found: {len(meals)}")
```

### Issue 2: Incorrect Analytics Results

#### Symptoms
- Results don't match expected patterns
- Severity levels seem wrong
- Evidence doesn't support conclusions

#### Validation Steps
```bash
# Review analytics evidence
curl "https://your-domain.com/api/v1/analytics/PATIENT_ID?user_role=clinician" | jq '.[] | .evidence'

# Check clinical thresholds
curl "https://your-domain.com/api/v1/health" | jq '.clinical_thresholds'
```

#### Common Issues

**Threshold Misconfiguration**
```bash
# Check environment variables
echo $POSTPRANDIAL_THRESHOLD  # Should be 180.0
echo $MISTIMED_BOLUS_THRESHOLD  # Should be 160.0
```

**Time Zone Issues**
```python
# Check timestamp consistency
import pandas as pd
df = pd.read_csv('your_data.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Look for timezone issues
print(df['timestamp'].dt.tz)
# Should be consistent timezone or UTC
```

### Issue 3: Analytics Processing Timeouts

#### Symptoms
- Upload succeeds but analytics fail
- Timeout errors during processing
- Partial results returned

#### Solutions

**Optimize File Size**
```bash
# Reduce data to essential columns
cut -d',' -f1,2,3 large_file.csv > optimized_file.csv

# Split large files by date range
awk -F',' 'NR==1 || $1 ~ /2024-01/' large_file.csv > january_data.csv
```

**Check System Resources**
```bash
# Monitor during processing
docker stats trutrend-api

# Check memory usage
free -h

# Check disk space
df -h
```

---

## System Administration Issues

### Issue 1: Application Won't Start

#### Symptoms
- Docker container fails to start
- "Application startup failed" errors
- Health check fails

#### Diagnosis
```bash
# Check container status
docker-compose ps

# Review startup logs
docker-compose logs trutrend-api

# Check environment variables
docker exec trutrend-api env | grep -E "(DATABASE|SECRET|ENCRYPTION)"
```

#### Common Solutions

**Environment Variable Issues**
```bash
# Verify required variables are set
cat .env | grep -E "(DATABASE_URL|SECRET_KEY|ENCRYPTION_KEY)"

# Test database connection
docker exec trutrend-api python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

**Port Conflicts**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill conflicting process
sudo kill -9 $(lsof -t -i:8000)
```

**Database Issues**
```bash
# Check database status
docker-compose logs postgres

# Test database connectivity
docker exec trutrend-postgres pg_isready -U postgres
```

### Issue 2: Database Connection Problems

#### Symptoms
- "Database connection failed" errors
- Slow query performance
- Connection timeouts

#### Solutions

**Connection String Issues**
```bash
# Verify database URL format
echo $DATABASE_URL
# Should be: postgresql://user:password@host:port/database

# Test connection manually
psql $DATABASE_URL -c "SELECT 1;"
```

**Database Performance**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check slow queries
SELECT query, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 5;

-- Check database size
SELECT pg_size_pretty(pg_database_size(current_database()));
```

### Issue 3: SSL/TLS Certificate Issues

#### Symptoms
- "Certificate expired" warnings
- "Insecure connection" errors
- HTTPS redirect failures

#### Solutions

**Certificate Renewal**
```bash
# Check certificate expiration
openssl x509 -in /path/to/cert.pem -text -noout | grep "Not After"

# Renew Let's Encrypt certificate
sudo certbot renew

# Update Docker volume
sudo cp /etc/letsencrypt/live/your-domain.com/* /opt/trutrend/nginx/ssl/
docker-compose restart nginx
```

**Certificate Validation**
```bash
# Test SSL configuration
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check certificate chain
curl -I https://your-domain.com
```

---

## Performance Issues

### Issue 1: Slow API Response Times

#### Symptoms
- API calls take >5 seconds
- User interface feels sluggish
- Timeout errors

#### Diagnosis
```bash
# Measure API response times
time curl "https://your-domain.com/api/v1/health"

# Check server resources
top
df -h
free -m
```

#### Solutions

**Application Optimization**
```bash
# Check application metrics
docker stats trutrend-api

# Monitor memory usage
docker exec trutrend-api ps aux --sort=-%mem | head

# Review slow endpoints
docker-compose logs trutrend-api | grep "slow\|performance"
```

**Database Optimization**
```sql
-- Check slow queries
SELECT query, calls, mean_exec_time 
FROM pg_stat_statements 
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC;

-- Analyze table statistics
ANALYZE;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public';
```

### Issue 2: High Memory Usage

#### Symptoms
- Out of memory errors
- Application crashes
- Slow system performance

#### Solutions

**Memory Monitoring**
```bash
# Check memory usage by process
ps aux --sort=-%mem | head

# Monitor Docker container resources
docker stats --no-stream

# Check system memory
free -h
```

**Memory Optimization**
```bash
# Limit Docker container memory
docker run --memory=1g trutrend-mvp

# Check for memory leaks
docker exec trutrend-api python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

### Issue 3: File Upload Performance

#### Symptoms
- Large file uploads timeout
- Upload progress is very slow
- Browser crashes during upload

#### Solutions

**Upload Optimization**
```bash
# Check upload limits
curl -I https://your-domain.com/api/v1/upload-csv

# Test with smaller files
split -l 500 large_file.csv smaller_
```

**Server Configuration**
```nginx
# Nginx configuration for large uploads
client_max_body_size 50M;
client_body_timeout 60s;
proxy_read_timeout 60s;
```

---

## Security and Access Issues

### Issue 1: CORS Errors

#### Symptoms
- "CORS policy" errors in browser
- Cross-origin request blocked
- API accessible via curl but not browser

#### Solutions

**Check CORS Configuration**
```python
# In main.py, verify CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

**Test CORS Headers**
```bash
# Check CORS headers
curl -H "Origin: https://your-frontend.com" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS \
  https://your-domain.com/api/v1/upload-csv
```

### Issue 2: Rate Limiting Issues

#### Symptoms
- "Too many requests" errors
- API calls rejected after several attempts
- 429 status code responses

#### Solutions

**Check Rate Limits**
```bash
# Test rate limiting
for i in {1..20}; do
  curl -w "%{http_code}\n" https://your-domain.com/api/v1/health
  sleep 1
done
```

**Adjust Rate Limits**
```nginx
# Nginx rate limiting configuration
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

### Issue 3: Data Privacy Concerns

#### Symptoms
- Audit trail gaps
- Unencrypted data found
- Privacy compliance issues

#### Solutions

**Verify Encryption**
```python
# Test data encryption
from app.core.security import security_manager

# Test encryption functionality
test_data = "sensitive_patient_data"
encrypted = security_manager.encrypt_sensitive_data(test_data)
decrypted = security_manager.decrypt_sensitive_data(encrypted)
assert test_data == decrypted
print("Encryption working correctly")
```

**Check Audit Logging**
```bash
# Review audit logs
docker-compose logs trutrend-api | grep "AUDIT:"

# Verify patient ID hashing
grep "patient_id" /var/log/trutrend/audit.log
# Should show hashed IDs, not plain text
```

---

## Integration Problems

### Issue 1: EMR Integration Issues

#### Symptoms
- Data not syncing with EMR
- Authentication failures
- API compatibility issues

#### Solutions

**Check Integration Endpoints**
```bash
# Test EMR API connectivity
curl -H "Authorization: Bearer $EMR_TOKEN" \
  https://emr-api.example.com/api/v1/patients

# Verify data format compatibility
curl -X POST https://emr-api.example.com/api/v1/analytics \
  -H "Content-Type: application/json" \
  -d @sample_analytics.json
```

### Issue 2: Device Data Sync Issues

#### Symptoms
- Missing data from specific devices
- Sync delays or failures
- Incomplete data sets

#### Solutions

**Verify Device API Access**
```bash
# Test Dexcom API
curl -H "Authorization: Bearer $DEXCOM_TOKEN" \
  https://api.dexcom.com/v2/users/self/egvs

# Test Glooko API
curl -H "Authorization: Bearer $GLOOKO_TOKEN" \
  https://api.glooko.com/v1/patients/data
```

---

## Emergency Procedures

### Critical System Failure

#### Immediate Actions
1. **Assess impact**: Patient data access affected?
2. **Check health status**: `curl https://your-domain.com/api/v1/health`
3. **Review logs**: `docker-compose logs --tail=100`
4. **Notify stakeholders**: Send status update
5. **Implement backup**: Switch to backup system if available

#### Emergency Contacts
- **System Administrator**: admin@trutrend.health
- **On-call Engineer**: +1-XXX-XXX-XXXX
- **Emergency Hotline**: 1-800-TRUTREND-EMERGENCY

### Data Loss Prevention

#### Backup Verification
```bash
# Check recent backups
ls -la /backup/directory/ | head -10

# Test backup restoration
./scripts/test-backup-restore.sh

# Verify backup integrity
gpg --verify backup_file.gpg
```

#### Emergency Backup
```bash
# Create emergency backup
./scripts/emergency-backup.sh

# Upload to secure location
aws s3 cp emergency_backup.tar.gz s3://emergency-backup-bucket/
```

### Security Incident Response

#### Immediate Actions
1. **Isolate affected systems**: Disconnect from network if needed
2. **Preserve evidence**: Take system snapshots
3. **Notify security team**: security@trutrend.health
4. **Document incident**: Record all actions taken
5. **Follow incident response plan**: Execute documented procedures

#### Evidence Collection
```bash
# Collect system logs
journalctl --since "1 hour ago" > incident_logs.txt

# Network activity
netstat -an > network_connections.txt

# Process information
ps aux > running_processes.txt
```

---

## Getting Support

### Self-Service Resources

#### Documentation
- **API Documentation**: https://docs.trutrend.health/api
- **User Guides**: https://docs.trutrend.health/users
- **Knowledge Base**: https://help.trutrend.health
- **Video Tutorials**: https://learn.trutrend.health

#### Community Support
- **User Forums**: https://community.trutrend.health
- **Stack Overflow**: Tag questions with `trutrend`
- **GitHub Issues**: For open-source components
- **Discord Chat**: Real-time community help

### Professional Support

#### Support Levels

**Basic Support** (Free)
- Email support during business hours
- Community forum access
- Documentation and tutorials
- Response time: 48-72 hours

**Professional Support** (Paid)
- Priority email and phone support
- Direct access to technical team
- Custom integration assistance
- Response time: 4-8 hours

**Enterprise Support** (Paid)
- 24/7 phone support
- Dedicated support engineer
- On-site assistance available
- Response time: 1-2 hours

#### Contact Information

**General Support**
- Email: support@trutrend.health
- Phone: 1-800-TRUTREND
- Live Chat: Available on website
- Hours: Monday-Friday, 8 AM - 6 PM EST

**Technical Support**
- Email: technical@trutrend.health
- Phone: 1-800-TRUTREND ext. 2
- Emergency: 1-800-TRUTREND-EMERGENCY
- Available: 24/7 for enterprise customers

**Clinical Support**
- Email: clinical@trutrend.health
- Phone: 1-800-TRUTREND ext. 3
- Hours: Monday-Friday, 9 AM - 5 PM EST
- Staffed by: Certified diabetes educators

### When to Contact Support

#### Immediate Contact Required
- **System security breach** or suspected intrusion
- **Patient data loss** or corruption
- **Critical system failure** affecting patient care
- **HIPAA compliance** violations

#### Priority Contact (Same Day)
- **Application crashes** or severe performance issues
- **Data upload failures** affecting multiple users
- **Authentication** or access problems
- **Integration failures** with critical systems

#### Standard Contact (1-2 Business Days)
- **Feature requests** or enhancement suggestions
- **General usage** questions
- **Documentation** improvements
- **Training** requests

#### Information to Provide

**For Technical Issues**
- Error messages (exact text)
- Steps to reproduce the problem
- System information (browser, OS)
- File samples (if data-related)
- Screenshots or screen recordings

**For Data Issues**
- Patient ID (if applicable)
- File name and format
- Data source device
- Upload timestamp
- Error messages received

**For Performance Issues**
- Specific operations affected
- Time of occurrence
- Duration of issue
- System load during issue
- Network conditions

---

## Troubleshooting Tools and Scripts

### Diagnostic Scripts

#### System Health Check
```bash
#!/bin/bash
# health_check.sh

echo "TrueTrend System Health Check"
echo "============================="

# API Health
echo "Checking API health..."
API_STATUS=$(curl -s https://your-domain.com/api/v1/health | jq -r '.status')
echo "API Status: $API_STATUS"

# Database Health
echo "Checking database..."
DB_STATUS=$(docker exec trutrend-postgres pg_isready -U postgres)
echo "Database Status: $DB_STATUS"

# Disk Space
echo "Checking disk space..."
df -h | grep -E "/$|/opt"

# Memory Usage
echo "Checking memory..."
free -h

# Docker Services
echo "Checking Docker services..."
docker-compose ps
```

#### Log Analysis Tool
```bash
#!/bin/bash
# analyze_logs.sh

LOG_FILE="trutrend-api.log"
TIME_RANGE="1 hour ago"

echo "Analyzing logs from $TIME_RANGE"
echo "================================"

# Error count
echo "Error Summary:"
journalctl --since "$TIME_RANGE" | grep -c "ERROR"

# Most common errors
echo "Most Common Errors:"
journalctl --since "$TIME_RANGE" | grep "ERROR" | sort | uniq -c | sort -nr | head -5

# Performance issues
echo "Performance Issues:"
journalctl --since "$TIME_RANGE" | grep -E "slow|timeout|performance"
```

### Configuration Validation

#### Environment Validation Script
```python
#!/usr/bin/env python3
# validate_config.py

import os
import sys
from urllib.parse import urlparse

def validate_config():
    """Validate TrueTrend configuration."""
    errors = []
    
    # Required environment variables
    required_vars = [
        'DATABASE_URL',
        'SECRET_KEY',
        'ENCRYPTION_KEY'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")
    
    # Validate database URL
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        parsed = urlparse(db_url)
        if parsed.scheme != 'postgresql':
            errors.append("DATABASE_URL must use postgresql:// scheme")
    
    # Validate secret key length
    secret_key = os.getenv('SECRET_KEY', '')
    if len(secret_key) < 32:
        errors.append("SECRET_KEY should be at least 32 characters")
    
    # Validate encryption key
    encryption_key = os.getenv('ENCRYPTION_KEY', '')
    try:
        from cryptography.fernet import Fernet
        Fernet(encryption_key.encode())
    except Exception:
        errors.append("ENCRYPTION_KEY is not a valid Fernet key")
    
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  ❌ {error}")
        sys.exit(1)
    else:
        print("✅ Configuration validation passed")

if __name__ == "__main__":
    validate_config()
```

---

*This troubleshooting guide is regularly updated based on user feedback and common issues. For additional help, please contact our support team or visit our documentation portal.*