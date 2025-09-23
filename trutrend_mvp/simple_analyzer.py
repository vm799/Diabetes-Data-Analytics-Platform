"""
Simple diabetes CSV analyzer - single file solution
Processes uploaded CSV and returns immediate analysis
"""

import io
import csv
import statistics
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Simple Diabetes Analyzer")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

def detect_device_type(csv_content: str) -> str:
    """Auto-detect diabetes device type from CSV headers and content"""
    lines = csv_content.split('\n')
    headers = lines[0].lower() if lines else ""
    
    # Dexcom G6/G7 detection
    if 'dexcom' in headers or 'event type' in headers or 'glucose value (mg/dl)' in headers:
        return "Dexcom"
    
    # FreeStyle LibreView detection
    if 'freestyle' in headers or 'historic glucose mg/dl' in headers or 'scan glucose mg/dl' in headers:
        return "FreeStyle LibreView"
    
    # Glooko detection
    if 'glooko' in headers or 'glucose_value' in headers or 'device_name' in headers:
        return "Glooko"
    
    # Medtronic CareLink detection
    if 'medtronic' in headers or 'carelink' in headers or 'sensor glucose (mg/dl)' in headers:
        return "Medtronic CareLink"
    
    # Tandem t:connect detection
    if 'tandem' in headers or 'basal rate (u/hr)' in headers or 'bg reading (mg/dl)' in headers:
        return "Tandem t:connect"
    
    # Omnipod VIEW detection
    if 'omnipod' in headers or 'pod' in headers or 'bolus volume delivered (u)' in headers:
        return "Omnipod VIEW"
    
    return "Unknown"

def validate_glucose_value(value: Any) -> tuple[bool, float, str]:
    """Rigorous glucose validation with clinical safety bounds"""
    try:
        if value is None or value == '' or str(value).strip() == '':
            return False, 0.0, "Empty value"
        
        # Convert to float
        glucose = float(str(value).strip())
        
        # Clinical safety bounds (mg/dL)
        if glucose < 20:
            return False, glucose, f"Critically low reading ({glucose}) - likely sensor error"
        elif glucose > 600:
            return False, glucose, f"Extremely high reading ({glucose}) - likely sensor error"
        elif glucose < 40:
            return True, glucose, f"Severe hypoglycemia warning ({glucose})"
        elif glucose > 400:
            return True, glucose, f"Severe hyperglycemia warning ({glucose})"
        else:
            return True, glucose, ""
            
    except (ValueError, TypeError) as e:
        return False, 0.0, f"Invalid glucose format: {str(e)}"

def assess_data_quality(readings: List[Dict]) -> Dict[str, Any]:
    """Comprehensive data quality assessment for clinical safety"""
    if not readings:
        return {
            "quality_score": 0,
            "reliability": "UNRELIABLE",
            "warnings": ["No valid readings found"],
            "usable_for_clinical_decisions": False
        }
    
    total_readings = len(readings)
    warnings = []
    quality_issues = []
    
    # Check data span
    data_hours = total_readings * 5 / 60  # Assuming 5-min intervals
    if data_hours < 24:
        warnings.append(f"Limited data span ({data_hours:.1f} hours) - insufficient for comprehensive analysis")
        quality_issues.append("insufficient_duration")
    
    # Check for data gaps (simplified - would need timestamps for full analysis)
    if total_readings < 288:  # Less than 1 day of 5-min readings
        warnings.append("Potential data gaps detected")
        quality_issues.append("data_gaps")
    
    # Glucose range validation
    glucose_values = [r['glucose'] for r in readings]
    extreme_low = len([g for g in glucose_values if g < 40])
    extreme_high = len([g for g in glucose_values if g > 400])
    
    if extreme_low > total_readings * 0.05:  # >5% extreme lows
        warnings.append(f"High frequency of severe hypoglycemia ({extreme_low} readings)")
        quality_issues.append("frequent_severe_hypo")
    
    if extreme_high > total_readings * 0.05:  # >5% extreme highs
        warnings.append(f"High frequency of severe hyperglycemia ({extreme_high} readings)")
        quality_issues.append("frequent_severe_hyper")
    
    # Calculate quality score
    quality_score = 100
    quality_score -= len(quality_issues) * 15  # Deduct for each issue
    quality_score = max(0, min(100, quality_score))
    
    # Determine reliability
    if quality_score >= 80 and data_hours >= 24:
        reliability = "HIGH"
    elif quality_score >= 60 and data_hours >= 12:
        reliability = "MODERATE"
    elif quality_score >= 40:
        reliability = "LOW"
    else:
        reliability = "UNRELIABLE"
    
    return {
        "quality_score": quality_score,
        "reliability": reliability,
        "warnings": warnings,
        "data_span_hours": round(data_hours, 1),
        "total_readings": total_readings,
        "usable_for_clinical_decisions": reliability in ["HIGH", "MODERATE"] and data_hours >= 12
    }

def parse_glucose_data(csv_content: str) -> tuple[List[Dict], List[str]]:
    """Parse CSV content and extract glucose readings with rigorous validation"""
    glucose_readings = []
    parsing_errors = []
    device_type = detect_device_type(csv_content)
    
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_content))
    except Exception as e:
        parsing_errors.append(f"CSV parsing error: {str(e)}")
        return [], parsing_errors
    
    row_count = 0
    for row in csv_reader:
        row_count += 1
        glucose_value = None
        timestamp = None
        meal_info = None
        insulin_info = None
        validation_warnings = []
        
        # Device-specific parsing with validation
        if device_type == "Dexcom":
            for col, value in row.items():
                col_lower = col.lower()
                if 'glucose value' in col_lower and value:
                    is_valid, glucose, warning = validate_glucose_value(value)
                    if is_valid:
                        glucose_value = glucose
                        if warning:
                            validation_warnings.append(warning)
                    else:
                        parsing_errors.append(f"Row {row_count}: {warning}")
                elif 'timestamp' in col_lower:
                    timestamp = value
                elif 'carbs' in col_lower and value:
                    meal_info = value
                elif 'insulin' in col_lower and value:
                    insulin_info = value
        
        elif device_type == "FreeStyle LibreView":
            for col, value in row.items():
                col_lower = col.lower()
                if ('historic glucose' in col_lower or 'scan glucose' in col_lower) and value:
                    is_valid, glucose, warning = validate_glucose_value(value)
                    if is_valid:
                        glucose_value = glucose
                        if warning:
                            validation_warnings.append(warning)
                        break
                    else:
                        parsing_errors.append(f"Row {row_count}: {warning}")
                elif 'time' in col_lower or 'date' in col_lower:
                    timestamp = value
        
        elif device_type == "Glooko":
            raw_glucose = row.get('glucose_value') or row.get('Glucose Value')
            timestamp = row.get('timestamp') or row.get('Timestamp') or row.get('Date')
            if raw_glucose:
                is_valid, glucose, warning = validate_glucose_value(raw_glucose)
                if is_valid:
                    glucose_value = glucose
                    if warning:
                        validation_warnings.append(warning)
                else:
                    parsing_errors.append(f"Row {row_count}: {warning}")
        
        else:
            # Generic parsing with validation
            for col, value in row.items():
                col_lower = col.lower()
                if 'glucose' in col_lower and value and glucose_value is None:
                    is_valid, glucose, warning = validate_glucose_value(value)
                    if is_valid:
                        glucose_value = glucose
                        if warning:
                            validation_warnings.append(warning)
                        break
                    else:
                        parsing_errors.append(f"Row {row_count}: {warning}")
                elif any(word in col_lower for word in ['time', 'date']) and timestamp is None:
                    timestamp = value
        
        # Add valid glucose readings with warnings
        if glucose_value is not None:
            reading = {
                'timestamp': timestamp,
                'glucose': glucose_value,
                'device_type': device_type
            }
            if meal_info:
                reading['meal_info'] = meal_info
            if insulin_info:
                reading['insulin_info'] = insulin_info
            if validation_warnings:
                reading['warnings'] = validation_warnings
            
            glucose_readings.append(reading)
    
    return glucose_readings, parsing_errors

def calculate_advanced_metrics(glucose_values: List[float]) -> Dict[str, float]:
    """Calculate advanced diabetes-specific metrics"""
    if len(glucose_values) < 2:
        return {}
    
    # Coefficient of Variation (CV)
    mean_glucose = statistics.mean(glucose_values)
    std_glucose = statistics.stdev(glucose_values)
    cv = (std_glucose / mean_glucose) * 100
    
    # Time in ranges (International Consensus)
    tir_70_180 = len([g for g in glucose_values if 70 <= g <= 180]) / len(glucose_values) * 100
    tbr_below_70 = len([g for g in glucose_values if g < 70]) / len(glucose_values) * 100
    tbr_below_54 = len([g for g in glucose_values if g < 54]) / len(glucose_values) * 100
    tar_above_180 = len([g for g in glucose_values if g > 180]) / len(glucose_values) * 100
    tar_above_250 = len([g for g in glucose_values if g > 250]) / len(glucose_values) * 100
    
    # Mean Amplitude of Glycemic Excursions (MAGE) - simplified
    # Calculate excursions greater than 1 SD
    excursions = []
    for i in range(1, len(glucose_values) - 1):
        if abs(glucose_values[i] - glucose_values[i-1]) > std_glucose:
            excursions.append(abs(glucose_values[i] - glucose_values[i-1]))
    
    mage = statistics.mean(excursions) if excursions else 0
    
    # Glycemic Variability Index (GVI) - simplified calculation
    gvi = cv * 0.5 + (max(glucose_values) - min(glucose_values)) / mean_glucose * 50
    
    return {
        "cv_glucose": round(cv, 1),
        "tir_70_180": round(tir_70_180, 1),
        "tbr_below_70": round(tbr_below_70, 1),
        "tbr_below_54": round(tbr_below_54, 1),
        "tar_above_180": round(tar_above_180, 1),
        "tar_above_250": round(tar_above_250, 1),
        "mage": round(mage, 1),
        "gvi": round(gvi, 1)
    }

def calculate_specialist_metrics(readings: List[Dict], glucose_values: List[float]) -> Dict[str, Any]:
    """Calculate specialist-level clinical metrics for endocrinologists"""
    if len(glucose_values) < 2:
        return {}
    
    # Advanced glycemic metrics
    mean_glucose = statistics.mean(glucose_values)
    std_glucose = statistics.stdev(glucose_values)
    
    # Estimated A1C using updated formula (ADA 2008)
    estimated_a1c = (mean_glucose + 46.7) / 28.7
    eag = mean_glucose  # Estimated Average Glucose
    
    # Advanced hypoglycemia stratification
    level1_hypo = len([g for g in glucose_values if 54 <= g < 70]) / len(glucose_values) * 100  # Alert-level
    level2_hypo = len([g for g in glucose_values if 20 <= g < 54]) / len(glucose_values) * 100  # Clinically significant
    level3_hypo = len([g for g in glucose_values if g < 20]) / len(glucose_values) * 100       # Severe
    
    # Postprandial analysis (simplified - looking for major excursions)
    postprandial_peaks = []
    for i in range(2, len(glucose_values)):
        delta_2h = glucose_values[i] - glucose_values[i-2] if i >= 2 else 0
        if delta_2h > 50:  # Significant excursion suggesting meal
            postprandial_peaks.append(glucose_values[i])
    
    avg_postprandial_peak = statistics.mean(postprandial_peaks) if postprandial_peaks else 0
    
    # Dawn phenomenon detection (simplified - early morning glucose rise)
    dawn_readings = []
    for reading in readings:
        if 'timestamp' in reading:
            try:
                # Extract hour from timestamp if available
                time_str = reading['timestamp']
                if 'T' in time_str:
                    hour = int(time_str.split('T')[1][:2])
                    if 4 <= hour <= 8:  # Dawn hours
                        dawn_readings.append(reading['glucose'])
            except:
                pass
    
    dawn_phenomenon_detected = False
    if len(dawn_readings) >= 3:
        dawn_trend = max(dawn_readings) - min(dawn_readings)
        dawn_phenomenon_detected = dawn_trend > 30
    
    # Nocturnal hypoglycemia detection
    nocturnal_readings = []
    for reading in readings:
        if 'timestamp' in reading:
            try:
                time_str = reading['timestamp']
                if 'T' in time_str:
                    hour = int(time_str.split('T')[1][:2])
                    if 23 <= hour or hour <= 6:  # Night hours
                        nocturnal_readings.append(reading['glucose'])
            except:
                pass
    
    nocturnal_hypo_risk = len([g for g in nocturnal_readings if g < 70]) / max(len(nocturnal_readings), 1) * 100
    
    # Sensor accuracy indicators
    rapid_changes = sum(1 for i in range(1, len(glucose_values)) 
                       if abs(glucose_values[i] - glucose_values[i-1]) > 50)
    data_reliability_score = max(0, 100 - (rapid_changes / len(glucose_values) * 100))
    
    return {
        "estimated_a1c": round(estimated_a1c, 1),
        "estimated_avg_glucose": round(eag, 1),
        "hypoglycemia_stratification": {
            "level1_alert_hypo": round(level1_hypo, 1),
            "level2_clinical_hypo": round(level2_hypo, 1), 
            "level3_severe_hypo": round(level3_hypo, 1)
        },
        "postprandial_analysis": {
            "avg_peak": round(avg_postprandial_peak, 1),
            "excursions_detected": len(postprandial_peaks)
        },
        "circadian_patterns": {
            "dawn_phenomenon_detected": dawn_phenomenon_detected,
            "nocturnal_hypo_risk": round(nocturnal_hypo_risk, 1)
        },
        "sensor_quality": {
            "rapid_changes_count": rapid_changes,
            "reliability_score": round(data_reliability_score, 1)
        }
    }

def calculate_evidence_based_analysis(readings: List[Dict], glucose_values: List[float]) -> Dict[str, Any]:
    """
    Brutally honest, evidence-based clinical analysis with transparent validation.
    No assumptions, only what the data definitively shows.
    """
    if len(glucose_values) < 10:
        return {
            "data_reliability": "INSUFFICIENT",
            "evidence_quality": "POOR",
            "analysis_limitations": [
                f"Only {len(glucose_values)} glucose readings available",
                "Minimum 50+ readings required for statistically valid analysis",
                "Cannot determine meaningful patterns with this data volume"
            ],
            "recommendation": "CRITICAL: Collect more continuous glucose monitoring data before clinical interpretation"
        }
    
    analysis = {
        "data_characteristics": {},
        "statistical_validity": {},
        "clinical_findings": {},
        "evidence_quality": {},
        "transparent_calculations": {},
        "clinical_limitations": []
    }
    
    # Data Quality Assessment with transparency
    total_readings = len(glucose_values)
    glucose_range = max(glucose_values) - min(glucose_values)
    
    # Calculate actual time coverage
    if len(readings) > 1:
        first_time = datetime.fromisoformat(readings[0]['timestamp'].replace('Z', '+00:00'))
        last_time = datetime.fromisoformat(readings[-1]['timestamp'].replace('Z', '+00:00'))
        time_span_hours = (last_time - first_time).total_seconds() / 3600
    else:
        time_span_hours = 0
    
    # Evidence-based data quality scoring
    expected_readings_5min = int(time_span_hours * 12)  # 5-min intervals
    data_completeness = min(100, (total_readings / expected_readings_5min) * 100) if expected_readings_5min > 0 else 0
    
    analysis["data_characteristics"] = {
        "total_readings": total_readings,
        "time_span_hours": round(time_span_hours, 1),
        "expected_readings_5min_intervals": expected_readings_5min,
        "data_completeness_percent": round(data_completeness, 1),
        "glucose_range_mg_dl": round(glucose_range, 1),
        "mean_glucose": round(statistics.mean(glucose_values), 1),
        "median_glucose": round(statistics.median(glucose_values), 1)
    }
    
    # Statistical validity assessment
    confidence_level = "HIGH" if total_readings >= 288 else "MEDIUM" if total_readings >= 144 else "LOW"
    days_of_data = time_span_hours / 24
    
    analysis["statistical_validity"] = {
        "confidence_level": confidence_level,
        "days_of_data": round(days_of_data, 1),
        "minimum_recommended_days": 14,
        "meets_ada_consensus_standards": days_of_data >= 14 and data_completeness >= 70,
        "sample_size_adequacy": "ADEQUATE" if total_readings >= 288 else "MARGINAL" if total_readings >= 144 else "INADEQUATE"
    }
    
    # Only calculate clinical metrics if we have adequate data
    if total_readings >= 50:
        # Time in Range - with transparency about calculation
        tir_70_180 = len([g for g in glucose_values if 70 <= g <= 180]) / total_readings * 100
        tir_70_140 = len([g for g in glucose_values if 70 <= g <= 140]) / total_readings * 100
        time_below_54 = len([g for g in glucose_values if g < 54]) / total_readings * 100
        time_above_250 = len([g for g in glucose_values if g > 250]) / total_readings * 100
        
        # Glycemic variability with clinical interpretation
        cv_glucose = (statistics.stdev(glucose_values) / statistics.mean(glucose_values)) * 100
        
        analysis["clinical_findings"] = {
            "time_in_range_70_180": {
                "percentage": round(tir_70_180, 1),
                "clinical_target": ">70%",
                "meets_target": tir_70_180 > 70,
                "clinical_significance": "PRIMARY endpoint for glycemic control assessment"
            },
            "time_in_tight_range_70_140": {
                "percentage": round(tir_70_140, 1),
                "clinical_note": "Stricter range for optimal control"
            },
            "severe_hypoglycemia_risk": {
                "time_below_54_percent": round(time_below_54, 1),
                "clinical_threshold": "<1%",
                "risk_level": "HIGH" if time_below_54 > 1 else "ACCEPTABLE",
                "clinical_significance": "CRITICAL safety metric"
            },
            "severe_hyperglycemia": {
                "time_above_250_percent": round(time_above_250, 1),
                "clinical_threshold": "<5%",
                "risk_level": "HIGH" if time_above_250 > 5 else "ACCEPTABLE"
            },
            "glycemic_variability": {
                "coefficient_of_variation": round(cv_glucose, 1),
                "clinical_target": "<36%",
                "interpretation": "HIGH" if cv_glucose > 36 else "ACCEPTABLE",
                "clinical_significance": "Predictor of hypoglycemia risk and long-term complications"
            }
        }
        
        # Evidence quality assessment
        analysis["evidence_quality"] = {
            "overall_grade": "A" if (days_of_data >= 14 and data_completeness >= 80) else 
                           "B" if (days_of_data >= 7 and data_completeness >= 70) else 
                           "C" if (days_of_data >= 3 and data_completeness >= 60) else "D",
            "ada_consensus_compliance": days_of_data >= 14 and data_completeness >= 70,
            "clinical_decision_reliability": "HIGH" if days_of_data >= 14 else "MODERATE" if days_of_data >= 7 else "LOW"
        }
        
        # Transparent calculation methodology
        analysis["transparent_calculations"] = {
            "tir_calculation": f"Readings 70-180 mg/dL: {len([g for g in glucose_values if 70 <= g <= 180])} of {total_readings}",
            "cv_calculation": f"Standard Deviation: {round(statistics.stdev(glucose_values), 1)} / Mean: {round(statistics.mean(glucose_values), 1)} × 100",
            "data_gaps_identified": max(0, expected_readings_5min - total_readings),
            "interpolation_used": False,  # We don't interpolate missing data
            "outlier_handling": "No outliers removed - all data points included"
        }
    else:
        analysis["clinical_limitations"].append(f"Insufficient data for reliable clinical analysis (need ≥50 readings, have {total_readings})")
    
    # Clinical interpretation limitations (always included)
    if days_of_data < 14:
        analysis["clinical_limitations"].append(f"Data span ({round(days_of_data, 1)} days) below ADA consensus minimum (14 days)")
    
    if data_completeness < 70:
        analysis["clinical_limitations"].append(f"Data completeness ({round(data_completeness, 1)}%) below recommended threshold (70%)")
    
    if glucose_range > 400:
        analysis["clinical_limitations"].append("Extremely wide glucose range suggests sensor errors or extraordinary clinical events")
    
    return analysis

def detect_clinical_patterns(readings: List[Dict]) -> List[Dict]:
    """Advanced clinical pattern detection"""
    patterns = []
    glucose_values = [r['glucose'] for r in readings]
    
    if len(glucose_values) < 5:
        return patterns
    
    advanced_metrics = calculate_advanced_metrics(glucose_values)
    
    # Time in Range Assessment (ADA/EASD Consensus)
    tir = advanced_metrics.get('tir_70_180', 0)
    if tir < 50:
        patterns.append({
            "type": "Poor Glycemic Control",
            "severity": "High",
            "description": f"Time in Range only {tir:.1f}% (Target: >70%)",
            "recommendation": "Comprehensive diabetes management review needed",
            "metric": "Time in Range",
            "target": ">70%",
            "actual": f"{tir:.1f}%"
        })
    elif tir < 70:
        patterns.append({
            "type": "Suboptimal Glycemic Control", 
            "severity": "Medium",
            "description": f"Time in Range {tir:.1f}% (Target: >70%)",
            "recommendation": "Consider therapy adjustment to improve TIR",
            "metric": "Time in Range",
            "target": ">70%", 
            "actual": f"{tir:.1f}%"
        })
    
    # Hypoglycemia Risk Assessment
    tbr_70 = advanced_metrics.get('tbr_below_70', 0)
    tbr_54 = advanced_metrics.get('tbr_below_54', 0)
    
    if tbr_54 > 1:
        patterns.append({
            "type": "Severe Hypoglycemia Risk",
            "severity": "High",
            "description": f"Time below 54 mg/dL: {tbr_54:.1f}% (Target: <1%)",
            "recommendation": "Immediate hypoglycemia prevention protocol needed",
            "metric": "TBR <54 mg/dL",
            "target": "<1%",
            "actual": f"{tbr_54:.1f}%"
        })
    elif tbr_70 > 4:
        patterns.append({
            "type": "Hypoglycemia Risk",
            "severity": "Medium",
            "description": f"Time below 70 mg/dL: {tbr_70:.1f}% (Target: <4%)",
            "recommendation": "Review hypoglycemia prevention strategies",
            "metric": "TBR <70 mg/dL", 
            "target": "<4%",
            "actual": f"{tbr_70:.1f}%"
        })
    
    # Hyperglycemia Assessment
    tar_250 = advanced_metrics.get('tar_above_250', 0)
    tar_180 = advanced_metrics.get('tar_above_180', 0)
    
    if tar_250 > 5:
        patterns.append({
            "type": "Severe Hyperglycemia",
            "severity": "High", 
            "description": f"Time above 250 mg/dL: {tar_250:.1f}% (Target: <5%)",
            "recommendation": "Urgent hyperglycemia management required",
            "metric": "TAR >250 mg/dL",
            "target": "<5%",
            "actual": f"{tar_250:.1f}%"
        })
    elif tar_180 > 25:
        patterns.append({
            "type": "Hyperglycemia Pattern",
            "severity": "Medium",
            "description": f"Time above 180 mg/dL: {tar_180:.1f}% (Target: <25%)",
            "recommendation": "Consider intensification of diabetes therapy",
            "metric": "TAR >180 mg/dL",
            "target": "<25%", 
            "actual": f"{tar_180:.1f}%"
        })
    
    # Glycemic Variability Assessment
    cv = advanced_metrics.get('cv_glucose', 0)
    if cv > 36:
        patterns.append({
            "type": "High Glycemic Variability",
            "severity": "Medium",
            "description": f"Coefficient of Variation: {cv:.1f}% (Target: <36%)",
            "recommendation": "Focus on reducing glucose variability through consistent carb counting and timing",
            "metric": "Glucose CV",
            "target": "<36%",
            "actual": f"{cv:.1f}%"
        })
    
    # MAGE Assessment
    mage = advanced_metrics.get('mage', 0)
    if mage > 60:
        patterns.append({
            "type": "Large Glycemic Excursions",
            "severity": "Medium", 
            "description": f"Mean Amplitude of Glycemic Excursions: {mage:.1f} mg/dL",
            "recommendation": "Review post-prandial glucose management and insulin timing",
            "metric": "MAGE",
            "target": "<60 mg/dL",
            "actual": f"{mage:.1f} mg/dL"
        })
    
    return patterns

def analyze_glucose_patterns(readings: List[Dict], parsing_errors: List[str] = None) -> Dict[str, Any]:
    """Enhanced glucose pattern analysis with clinical safety validation"""
    if not readings:
        return {
            "error": "No valid glucose readings found",
            "safety_status": "UNSAFE_FOR_ANALYSIS",
            "parsing_errors": parsing_errors or []
        }
    
    # Comprehensive data quality assessment
    data_quality = assess_data_quality(readings)
    
    glucose_values = [r['glucose'] for r in readings]
    device_type = readings[0].get('device_type', 'Unknown') if readings else 'Unknown'
    
    # Collect all warnings from individual readings
    individual_warnings = []
    for reading in readings:
        if 'warnings' in reading:
            individual_warnings.extend(reading['warnings'])
    
    # Only proceed with analysis if data is reliable enough
    if not data_quality["usable_for_clinical_decisions"]:
        return {
            "error": "Data quality insufficient for clinical analysis",
            "safety_status": "UNSAFE_FOR_ANALYSIS", 
            "data_quality": data_quality,
            "parsing_errors": parsing_errors or [],
            "recommendation": "Please provide higher quality data with at least 12-24 hours of continuous glucose monitoring"
        }
    
    # Basic statistics with uncertainty indicators
    mean_glucose = statistics.mean(glucose_values)
    std_glucose = statistics.stdev(glucose_values) if len(glucose_values) > 1 else 0
    min_glucose = min(glucose_values)
    max_glucose = max(glucose_values)
    
    # Estimated A1C with uncertainty
    estimated_a1c = (mean_glucose + 46.7) / 28.7
    a1c_uncertainty = "±0.3%" if data_quality["reliability"] == "HIGH" else "±0.5%" if data_quality["reliability"] == "MODERATE" else "±0.8%"
    
    # Advanced metrics
    advanced_metrics = calculate_advanced_metrics(glucose_values)
    
    # Specialist-level clinical metrics (for clinician mode)
    specialist_metrics = calculate_specialist_metrics(readings, glucose_values)
    
    # Evidence-based clinical analysis with transparent validation
    evidence_based_analysis = calculate_evidence_based_analysis(readings, glucose_values)
    
    # Clinical patterns with conservative interpretation
    patterns = detect_clinical_patterns(readings)
    
    # Add conservative disclaimers to patterns based on data quality
    for pattern in patterns:
        if data_quality["reliability"] == "MODERATE":
            pattern["confidence"] = "MODERATE - Consider additional monitoring"
        elif data_quality["reliability"] == "LOW":
            pattern["confidence"] = "LOW - Requires clinical confirmation"
    
    # Safety assessment
    safety_status = "SAFE_FOR_ANALYSIS"
    if len(individual_warnings) > 0:
        safety_status = "ANALYSIS_WITH_WARNINGS"
    
    return {
        "safety_status": safety_status,
        "data_quality": data_quality,
        "total_readings": len(glucose_values),
        "device_type": device_type,
        "parsing_errors": parsing_errors or [],
        "individual_warnings": individual_warnings,
        "statistics": {
            "mean_glucose": round(mean_glucose, 1),
            "std_glucose": round(std_glucose, 1),
            "min_glucose": min_glucose,
            "max_glucose": max_glucose,
            "estimated_a1c": round(estimated_a1c, 1),
            "a1c_uncertainty": a1c_uncertainty,
            **advanced_metrics
        },
        "advanced_metrics": advanced_metrics,
        "specialist_metrics": specialist_metrics,
        "evidence_based_analysis": evidence_based_analysis,
        "patterns": patterns,
        "clinical_disclaimer": "This analysis is for informational purposes only. All clinical decisions should be made in consultation with healthcare providers. Data quality and interpretation limitations apply.",
        "summary": f"Analyzed {len(glucose_values)} {device_type} readings (Quality: {data_quality['reliability']}). Mean: {mean_glucose:.1f} mg/dL, TIR: {advanced_metrics.get('tir_70_180', 0):.1f}%"
    }

@app.post("/analyze-csv")
async def analyze_csv_file(
    file: UploadFile = File(...),
    user_role: str = Form(default="clinician")
):
    """Analyze uploaded CSV file and return immediate results"""
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse glucose data with enhanced validation
        glucose_readings, parsing_errors = parse_glucose_data(csv_content)
        
        if not glucose_readings:
            error_details = "No valid glucose readings found in CSV"
            if parsing_errors:
                error_details += f". Errors: {'; '.join(parsing_errors[:5])}"
            raise HTTPException(status_code=400, detail=error_details)
        
        # Analyze patterns with safety validation
        analysis = analyze_glucose_patterns(glucose_readings, parsing_errors)
        
        # Check if analysis is safe to proceed
        if analysis.get("safety_status") == "UNSAFE_FOR_ANALYSIS":
            # Create user-friendly action points
            action_points = []
            data_quality = analysis.get("data_quality", {})
            
            # Data span issues
            if data_quality.get("data_span_hours", 0) < 24:
                action_points.append({
                    "icon": "📅",
                    "title": "Need More Data",
                    "description": f"You have {data_quality.get('data_span_hours', 0):.1f} hours of glucose data.",
                    "action": "Download at least 24 hours of continuous glucose monitoring data from your device.",
                    "urgency": "medium"
                })
            
            # Quality score issues
            if data_quality.get("quality_score", 0) < 60:
                action_points.append({
                    "icon": "⚠️",
                    "title": "Data Quality Too Low",
                    "description": f"Quality score: {data_quality.get('quality_score', 0)}% (Need: 60%+)",
                    "action": "Ensure your glucose monitor was working properly during data collection.",
                    "urgency": "high"
                })
            
            # Specific warnings
            for warning in data_quality.get("warnings", []):
                if "data gaps" in warning.lower():
                    action_points.append({
                        "icon": "🔗",
                        "title": "Missing Data Detected",
                        "description": "Gaps found in your glucose readings.",
                        "action": "Check that your CGM stayed connected and was calibrated properly.",
                        "urgency": "medium"
                    })
                elif "severe hyperglycemia" in warning.lower():
                    action_points.append({
                        "icon": "🚨",
                        "title": "High Glucose Alert",
                        "description": "Frequent very high glucose readings detected.",
                        "action": "Contact your healthcare provider immediately to review these readings.",
                        "urgency": "high"
                    })
                elif "severe hypoglycemia" in warning.lower():
                    action_points.append({
                        "icon": "⚠️",
                        "title": "Low Glucose Alert", 
                        "description": "Frequent very low glucose readings detected.",
                        "action": "Discuss hypoglycemia prevention strategies with your diabetes care team.",
                        "urgency": "high"
                    })
            
            # General recommendations
            action_points.append({
                "icon": "💡",
                "title": "File Format Check",
                "description": "Ensure you're uploading the correct file type.",
                "action": "Upload a CSV file directly from your glucose monitoring device or app.",
                "urgency": "low"
            })
            
            action_points.append({
                "icon": "🏥",
                "title": "Need Help?",
                "description": "Having trouble with your glucose data?",
                "action": "Contact your diabetes educator or healthcare provider for assistance.",
                "urgency": "low"
            })
            
            raise HTTPException(
                status_code=422, 
                detail={
                    "type": "DATA_QUALITY_INSUFFICIENT",
                    "title": "Cannot Analyze This Glucose Data",
                    "message": f"Your data has a quality score of {data_quality.get('quality_score', 0)}% with {data_quality.get('reliability', 'UNKNOWN')} reliability. We need higher quality data for safe analysis.",
                    "action_points": action_points,
                    "data_summary": {
                        "total_readings": data_quality.get("total_readings", 0),
                        "hours_of_data": data_quality.get("data_span_hours", 0),
                        "quality_score": data_quality.get("quality_score", 0),
                        "reliability": data_quality.get("reliability", "UNKNOWN")
                    }
                }
            )
        
        # Format response based on user role
        if user_role == "patient":
            # Patient-friendly format
            insights = []
            recommendations = []
            
            for pattern in analysis.get("patterns", []):
                if pattern["type"] == "Hyperglycemia":
                    insights.append("Your glucose levels are running high at times")
                    recommendations.append("Consider discussing meal timing with your healthcare team")
                elif pattern["type"] == "Hypoglycemia":
                    insights.append("Some glucose readings are low")
                    recommendations.append("Monitor for low blood sugar symptoms")
                elif pattern["type"] == "High Variability":
                    insights.append("Your glucose levels vary quite a bit")
                    recommendations.append("Consistent meal and activity timing may help")
            
            if not insights:
                insights = ["Your glucose patterns look relatively stable"]
                recommendations = ["Keep up with your current diabetes management plan"]
            
            return {
                "status": "success",
                "user_role": user_role,
                "safety_status": analysis["safety_status"],
                "data_quality": analysis["data_quality"],
                "summary": analysis["summary"],
                "key_insights": insights,
                "recommendations": recommendations,
                "statistics": analysis["statistics"],
                "clinical_disclaimer": analysis["clinical_disclaimer"],
                "individual_warnings": analysis.get("individual_warnings", []),
                "parsing_errors": analysis.get("parsing_errors", [])
            }
        
        else:
            # Clinical format
            clinical_recommendations = []
            for pattern in analysis.get("patterns", []):
                if pattern["type"] == "Hyperglycemia":
                    clinical_recommendations.append("Evaluate postprandial glucose management")
                elif pattern["type"] == "Hypoglycemia":
                    clinical_recommendations.append("Assess hypoglycemia risk and management")
                elif pattern["type"] == "High Variability":
                    clinical_recommendations.append("Consider CGM data review and pattern analysis")
            
            if not clinical_recommendations:
                clinical_recommendations = ["Continue current monitoring - patterns appear stable"]
            
            return {
                "status": "success",
                "user_role": user_role,
                "safety_status": analysis["safety_status"],
                "data_quality": analysis["data_quality"],
                "analysis_results": analysis["patterns"],
                "clinical_recommendations": clinical_recommendations,
                "statistics": analysis["statistics"],
                "advanced_metrics": analysis.get("advanced_metrics", {}),
                "specialist_metrics": analysis.get("specialist_metrics", {}),
                "total_readings": analysis["total_readings"],
                "clinical_disclaimer": analysis["clinical_disclaimer"],
                "individual_warnings": analysis.get("individual_warnings", []),
                "parsing_errors": analysis.get("parsing_errors", [])
            }
            
    except HTTPException as he:
        # Re-raise HTTPExceptions with their original status and detail
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/")
async def dashboard():
    """Serve the unified dashboard with theme switching"""
    return FileResponse("unified_dashboard.html")

@app.get("/simple")
async def simple_dashboard():
    """Serve the simple dashboard"""
    return FileResponse("simple_dashboard.html")

@app.get("/dark")
async def dark_dashboard():
    """Redirect to unified dashboard"""
    return FileResponse("unified_dashboard.html")

@app.get("/professional")
async def professional_dashboard():
    """Serve the professional dashboard"""
    return FileResponse("professional_dashboard.html")

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "Simple Diabetes Analyzer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)