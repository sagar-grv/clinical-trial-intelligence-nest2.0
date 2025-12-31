"""
Configuration for Clinical Trial Intelligence System
"""
from pathlib import Path

# Data Lake Path
DATA_LAKE_PATH = Path(__file__).parent / "clinical_trial_data_lake"

# File Classification Keywords (Priority: Data Quality > Safety > Operational > Clinical)
FILE_CLASSIFICATION = {
    "Data Quality": ["missing", "inactive", "inactivated", "page"],
    "Safety": ["sae", "safety"],
    "Operational": ["visit", "projection"],
    "Clinical": ["edc", "metrics", "edrr", "coding", "medra", "whodd", "meddra"]
}

# Classification Priority (higher = more priority)
CLASSIFICATION_PRIORITY = {
    "Data Quality": 4,
    "Safety": 3,
    "Operational": 2,
    "Clinical": 1
}

# Identifier Standardization Mapping
IDENTIFIER_MAPPING = {
    "site_id": ["site", "site id", "site number", "siteid", "site_id", "site_number", "siteno", "site no"],
    "subject_id": ["subject", "subject id", "subjectid", "subject_id", "patient", "patient id", "patientid"],
    "visit": ["visit", "visit name", "visit number", "visitname", "visit_name", "visitno", "visit no"]
}

# Data Quality Issue Thresholds
QUALITY_THRESHOLDS = {
    "missing_lab_names": {"low": 1, "medium": 5, "high": 10},
    "missing_reference_ranges": {"low": 1, "medium": 5, "high": 10},
    "missing_crf_pages": {"low": 5, "medium": 15, "high": 30},
    "inactivated_forms": {"low": 3, "medium": 10, "high": 20}
}

# Operational Issue Thresholds
OPERATIONAL_THRESHOLDS = {
    "delayed_visits": {"low": 2, "medium": 5, "high": 10},
    "projection_slippage": {"low": 5, "medium": 15, "high": 25},  # percentage
    "query_backlog": {"low": 10, "medium": 30, "high": 50},
    "delayed_data_entry": {"low": 3, "medium": 7, "high": 14}  # days
}

# Risk Scoring Weights
RISK_WEIGHTS = {
    "data_quality": 0.5,
    "operational": 0.5
}

# Severity Colors
SEVERITY_COLORS = {
    "High": "#ef4444",
    "Medium": "#f59e0b", 
    "Low": "#22c55e"
}

# Risk Level Colors
RISK_COLORS = {
    "High Risk": "#dc2626",
    "Medium Risk": "#f97316",
    "Low Risk": "#16a34a"
}
