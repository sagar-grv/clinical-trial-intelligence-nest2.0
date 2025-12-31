"""
Data Quality Issue Detector - Identifies data quality problems
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import QUALITY_THRESHOLDS


class DataQualityDetector:
    """Detects data quality issues across clinical trial files."""
    
    def __init__(self):
        self.thresholds = QUALITY_THRESHOLDS
        self.issues: List[Dict] = []
    
    def classify_severity(self, count: int, issue_type: str) -> str:
        """Classify issue severity based on count and thresholds."""
        thresholds = self.thresholds.get(issue_type, {"low": 1, "medium": 5, "high": 10})
        
        if count >= thresholds["high"]:
            return "High"
        elif count >= thresholds["medium"]:
            return "Medium"
        elif count >= thresholds["low"]:
            return "Low"
        return "None"
    
    def detect_missing_lab_data(self, df: pd.DataFrame, file_name: str) -> List[Dict]:
        """Detect missing lab names and reference ranges."""
        issues = []
        
        if df is None or df.empty:
            return issues
        
        # Look for lab-related columns
        lab_name_cols = [c for c in df.columns if 'lab' in str(c).lower() and 'name' in str(c).lower()]
        range_cols = [c for c in df.columns if 'range' in str(c).lower() or 'reference' in str(c).lower()]
        
        # Check for missing lab names
        for col in lab_name_cols:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                severity = self.classify_severity(missing_count, "missing_lab_names")
                if severity != "None":
                    issues.append({
                        "type": "missing_lab_names",
                        "file": file_name,
                        "column": col,
                        "count": int(missing_count),
                        "severity": severity,
                        "description": f"{missing_count} missing lab names in column '{col}'"
                    })
        
        # Check for missing reference ranges
        for col in range_cols:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                severity = self.classify_severity(missing_count, "missing_reference_ranges")
                if severity != "None":
                    issues.append({
                        "type": "missing_reference_ranges",
                        "file": file_name,
                        "column": col,
                        "count": int(missing_count),
                        "severity": severity,
                        "description": f"{missing_count} missing reference ranges in column '{col}'"
                    })
        
        # Also check file name patterns
        if "missing" in file_name.lower() and "lab" in file_name.lower():
            total_rows = len(df)
            if total_rows > 0:
                severity = self.classify_severity(total_rows, "missing_lab_names")
                issues.append({
                    "type": "missing_lab_names",
                    "file": file_name,
                    "column": "All",
                    "count": int(total_rows),
                    "severity": severity,
                    "description": f"{total_rows} records in missing lab data file"
                })
        
        return issues
    
    def detect_missing_crf_pages(self, df: pd.DataFrame, file_name: str) -> List[Dict]:
        """Detect missing CRF pages."""
        issues = []
        
        if df is None or df.empty:
            return issues
        
        # Check if this is a missing pages file
        if "missing" in file_name.lower() and "page" in file_name.lower():
            # Count missing pages, potentially by site
            site_cols = [c for c in df.columns if 'site' in str(c).lower()]
            
            if site_cols:
                # Group by site
                site_col = site_cols[0]
                site_counts = df.groupby(site_col).size().to_dict()
                
                for site, count in site_counts.items():
                    severity = self.classify_severity(count, "missing_crf_pages")
                    if severity != "None":
                        issues.append({
                            "type": "missing_crf_pages",
                            "file": file_name,
                            "site_id": str(site),
                            "count": int(count),
                            "severity": severity,
                            "description": f"{count} missing CRF pages at Site {site}"
                        })
            else:
                # Total count
                count = len(df)
                severity = self.classify_severity(count, "missing_crf_pages")
                if severity != "None":
                    issues.append({
                        "type": "missing_crf_pages",
                        "file": file_name,
                        "count": int(count),
                        "severity": severity,
                        "description": f"{count} missing CRF pages total"
                    })
        
        return issues
    
    def detect_inactivated_forms(self, df: pd.DataFrame, file_name: str) -> List[Dict]:
        """Detect inactivated forms, folders, and records."""
        issues = []
        
        if df is None or df.empty:
            return issues
        
        # Check if this is an inactivated forms file
        if "inactive" in file_name.lower() or "inactivated" in file_name.lower():
            site_cols = [c for c in df.columns if 'site' in str(c).lower()]
            
            if site_cols:
                site_col = site_cols[0]
                site_counts = df.groupby(site_col).size().to_dict()
                
                for site, count in site_counts.items():
                    severity = self.classify_severity(count, "inactivated_forms")
                    if severity != "None":
                        issues.append({
                            "type": "inactivated_forms",
                            "file": file_name,
                            "site_id": str(site),
                            "count": int(count),
                            "severity": severity,
                            "description": f"{count} inactivated forms at Site {site}"
                        })
            else:
                count = len(df)
                severity = self.classify_severity(count, "inactivated_forms")
                if severity != "None":
                    issues.append({
                        "type": "inactivated_forms",
                        "file": file_name,
                        "count": int(count),
                        "severity": severity,
                        "description": f"{count} inactivated forms total"
                    })
        
        return issues
    
    def analyze_file(self, df: pd.DataFrame, file_name: str, category: str) -> List[Dict]:
        """Analyze a single file for data quality issues."""
        all_issues = []
        
        if category == "Data Quality":
            all_issues.extend(self.detect_missing_lab_data(df, file_name))
            all_issues.extend(self.detect_missing_crf_pages(df, file_name))
            all_issues.extend(self.detect_inactivated_forms(df, file_name))
        
        return all_issues
    
    def analyze_study(self, study_id: str, file_data: Dict[str, Tuple[pd.DataFrame, str]]) -> Dict:
        """
        Analyze all files in a study for data quality issues.
        file_data: Dict mapping file_name to (DataFrame, category)
        """
        study_issues = []
        site_issues: Dict[str, List[Dict]] = {}
        
        for file_name, (df, category) in file_data.items():
            issues = self.analyze_file(df, file_name, category)
            study_issues.extend(issues)
            
            # Group by site
            for issue in issues:
                site_id = issue.get("site_id", "Study-wide")
                if site_id not in site_issues:
                    site_issues[site_id] = []
                site_issues[site_id].append(issue)
        
        self.issues = study_issues
        
        return {
            "study_id": study_id,
            "total_issues": len(study_issues),
            "issues": study_issues,
            "by_site": site_issues,
            "by_type": self._group_by_type(study_issues),
            "by_severity": self._group_by_severity(study_issues)
        }
    
    def _group_by_type(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """Group issues by type."""
        grouped = {}
        for issue in issues:
            issue_type = issue.get("type", "unknown")
            if issue_type not in grouped:
                grouped[issue_type] = []
            grouped[issue_type].append(issue)
        return grouped
    
    def _group_by_severity(self, issues: List[Dict]) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {"High": 0, "Medium": 0, "Low": 0}
        for issue in issues:
            severity = issue.get("severity", "Low")
            counts[severity] = counts.get(severity, 0) + 1
        return counts
