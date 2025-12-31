"""
Operational Issue Detector - Identifies operational problems
"""
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OPERATIONAL_THRESHOLDS


class OperationalDetector:
    """Detects operational issues in clinical trial data."""
    
    def __init__(self):
        self.thresholds = OPERATIONAL_THRESHOLDS
        self.issues: List[Dict] = []
    
    def classify_severity(self, value: float, issue_type: str) -> str:
        """Classify issue severity based on value and thresholds."""
        thresholds = self.thresholds.get(issue_type, {"low": 1, "medium": 5, "high": 10})
        
        if value >= thresholds["high"]:
            return "High"
        elif value >= thresholds["medium"]:
            return "Medium"
        elif value >= thresholds["low"]:
            return "Low"
        return "None"
    
    def detect_visit_delays(self, df: pd.DataFrame, file_name: str) -> List[Dict]:
        """Detect delayed visit completions."""
        issues = []
        
        if df is None or df.empty:
            return issues
        
        # Look for visit projection/schedule files
        if "visit" not in file_name.lower():
            return issues
        
        # Look for date columns indicating delays
        date_cols = [c for c in df.columns if 'date' in str(c).lower()]
        status_cols = [c for c in df.columns if 'status' in str(c).lower() or 'complete' in str(c).lower()]
        site_cols = [c for c in df.columns if 'site' in str(c).lower()]
        
        # Check for projected vs actual dates
        projected_cols = [c for c in date_cols if 'project' in str(c).lower() or 'expected' in str(c).lower() or 'planned' in str(c).lower()]
        actual_cols = [c for c in date_cols if 'actual' in str(c).lower() or 'complete' in str(c).lower()]
        
        if projected_cols and actual_cols:
            # Compare dates to find delays
            try:
                proj_col = projected_cols[0]
                actual_col = actual_cols[0]
                
                df_copy = df.copy()
                df_copy[proj_col] = pd.to_datetime(df_copy[proj_col], errors='coerce')
                df_copy[actual_col] = pd.to_datetime(df_copy[actual_col], errors='coerce')
                
                # Calculate delays
                df_copy['delay_days'] = (df_copy[actual_col] - df_copy[proj_col]).dt.days
                delayed = df_copy[df_copy['delay_days'] > 0]
                
                if site_cols:
                    site_col = site_cols[0]
                    site_delays = delayed.groupby(site_col)['delay_days'].agg(['count', 'mean']).to_dict('index')
                    
                    for site, stats in site_delays.items():
                        count = stats.get('count', 0)
                        avg_delay = stats.get('mean', 0)
                        severity = self.classify_severity(count, "delayed_visits")
                        
                        if severity != "None":
                            issues.append({
                                "type": "delayed_visits",
                                "file": file_name,
                                "site_id": str(site),
                                "count": int(count),
                                "avg_delay_days": round(avg_delay, 1),
                                "severity": severity,
                                "description": f"Site {site}: {count} delayed visits (avg {round(avg_delay, 1)} days)"
                            })
                else:
                    total_delayed = len(delayed)
                    avg_delay = delayed['delay_days'].mean()
                    severity = self.classify_severity(total_delayed, "delayed_visits")
                    
                    if severity != "None":
                        issues.append({
                            "type": "delayed_visits",
                            "file": file_name,
                            "count": int(total_delayed),
                            "avg_delay_days": round(avg_delay, 1) if pd.notna(avg_delay) else 0,
                            "severity": severity,
                            "description": f"{total_delayed} delayed visits total"
                        })
            except Exception:
                pass
        
        # Check for slippage percentage column
        slippage_cols = [c for c in df.columns if 'slip' in str(c).lower() or 'variance' in str(c).lower()]
        if slippage_cols:
            try:
                slip_col = slippage_cols[0]
                df_copy = df.copy()
                df_copy[slip_col] = pd.to_numeric(df_copy[slip_col], errors='coerce')
                
                avg_slippage = df_copy[slip_col].abs().mean()
                severity = self.classify_severity(avg_slippage, "projection_slippage")
                
                if severity != "None":
                    issues.append({
                        "type": "projection_slippage",
                        "file": file_name,
                        "slippage_pct": round(avg_slippage, 1),
                        "severity": severity,
                        "description": f"Visit projection slippage: {round(avg_slippage, 1)}%"
                    })
            except Exception:
                pass
        
        return issues
    
    def detect_query_backlog(self, df: pd.DataFrame, file_name: str) -> List[Dict]:
        """Detect high query backlog from EDC metrics."""
        issues = []
        
        if df is None or df.empty:
            return issues
        
        if "edc" not in file_name.lower() and "metric" not in file_name.lower():
            return issues
        
        # Look for query-related columns
        query_cols = [c for c in df.columns if 'query' in str(c).lower() or 'open' in str(c).lower()]
        site_cols = [c for c in df.columns if 'site' in str(c).lower()]
        
        for col in query_cols:
            try:
                df_copy = df.copy()
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
                
                if site_cols:
                    site_col = site_cols[0]
                    site_queries = df_copy.groupby(site_col)[col].sum().to_dict()
                    
                    for site, query_count in site_queries.items():
                        if pd.notna(query_count):
                            severity = self.classify_severity(query_count, "query_backlog")
                            if severity != "None":
                                issues.append({
                                    "type": "query_backlog",
                                    "file": file_name,
                                    "site_id": str(site),
                                    "count": int(query_count),
                                    "severity": severity,
                                    "description": f"Site {site}: {int(query_count)} open queries"
                                })
                else:
                    total = df_copy[col].sum()
                    if pd.notna(total):
                        severity = self.classify_severity(total, "query_backlog")
                        if severity != "None":
                            issues.append({
                                "type": "query_backlog",
                                "file": file_name,
                                "count": int(total),
                                "severity": severity,
                                "description": f"{int(total)} open queries total"
                            })
            except Exception:
                pass
        
        return issues
    
    def detect_data_entry_delays(self, df: pd.DataFrame, file_name: str) -> List[Dict]:
        """Detect delayed data entry from EDC metrics or EDRR."""
        issues = []
        
        if df is None or df.empty:
            return issues
        
        if "edc" not in file_name.lower() and "edrr" not in file_name.lower():
            return issues
        
        # Look for entry delay columns
        delay_cols = [c for c in df.columns if 'delay' in str(c).lower() or 'lag' in str(c).lower() or 'days' in str(c).lower()]
        site_cols = [c for c in df.columns if 'site' in str(c).lower()]
        
        for col in delay_cols:
            try:
                df_copy = df.copy()
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
                
                if site_cols:
                    site_col = site_cols[0]
                    site_delays = df_copy.groupby(site_col)[col].mean().to_dict()
                    
                    for site, avg_delay in site_delays.items():
                        if pd.notna(avg_delay) and avg_delay > 0:
                            severity = self.classify_severity(avg_delay, "delayed_data_entry")
                            if severity != "None":
                                issues.append({
                                    "type": "delayed_data_entry",
                                    "file": file_name,
                                    "site_id": str(site),
                                    "avg_delay_days": round(avg_delay, 1),
                                    "severity": severity,
                                    "description": f"Site {site}: Avg {round(avg_delay, 1)} days data entry delay"
                                })
                else:
                    avg = df_copy[col].mean()
                    if pd.notna(avg) and avg > 0:
                        severity = self.classify_severity(avg, "delayed_data_entry")
                        if severity != "None":
                            issues.append({
                                "type": "delayed_data_entry",
                                "file": file_name,
                                "avg_delay_days": round(avg, 1),
                                "severity": severity,
                                "description": f"Avg {round(avg, 1)} days data entry delay"
                            })
            except Exception:
                pass
        
        return issues
    
    def analyze_file(self, df: pd.DataFrame, file_name: str, category: str) -> List[Dict]:
        """Analyze a single file for operational issues."""
        all_issues = []
        
        if category in ["Operational", "Clinical"]:
            all_issues.extend(self.detect_visit_delays(df, file_name))
            all_issues.extend(self.detect_query_backlog(df, file_name))
            all_issues.extend(self.detect_data_entry_delays(df, file_name))
        
        return all_issues
    
    def analyze_study(self, study_id: str, file_data: Dict[str, Tuple[pd.DataFrame, str]]) -> Dict:
        """
        Analyze all files in a study for operational issues.
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
