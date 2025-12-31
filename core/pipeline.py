"""
Processing Pipeline - Orchestrates extraction, analysis, and insight generation
"""
from typing import Dict, List, Optional
import io
import sys
import json
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.storage import DatabaseStorage
from database.models import ProcessingStatus
from core.table_extractor import TableExtractor
from core.standardizer import IdentifierStandardizer
from ai.gemini_client import GeminiClient


def json_serialize(obj):
    """Convert non-serializable objects to JSON-safe formats."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return str(obj)
    return str(obj)


def make_json_safe(data):
    """Recursively convert all values in data structure to JSON-safe formats."""
    if isinstance(data, dict):
        return {k: make_json_safe(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_json_safe(item) for item in data]
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif data is None or isinstance(data, (str, int, float, bool)):
        return data
    else:
        return str(data)


class ProcessingPipeline:
    """
    Enterprise processing pipeline for clinical trial files.
    
    Flow:
    1. Read file from database (source of truth)
    2. Extract all tables from all sheets
    3. Standardize identifiers
    4. Run analytics and detect issues
    5. Save results to database
    6. Generate AI insights
    """
    
    def __init__(self, db_path: str = "database/clinical_trials.db"):
        self.storage = DatabaseStorage(db_path)
        self.extractor = TableExtractor()
        self.standardizer = IdentifierStandardizer()
        self.gemini = GeminiClient()

    
    def process_file(self, file_id: int) -> Dict:
        """
        Process a single uploaded file end-to-end.
        
        Returns complete analysis results with traceability.
        """
        result = {
            "file_id": file_id,
            "success": False,
            "tables_extracted": 0,
            "issues_detected": 0,
            "unique_issues": 0,
            "risk_level": None,
            "audit": None,
            "errors": []
        }
        
        try:
            # Update status to processing
            self.storage.update_file_status(file_id, ProcessingStatus.PROCESSING)
            
            # Step 1: Get file from database
            file_blob = self.storage.get_file_blob(file_id)
            if not file_blob:
                raise ValueError(f"File {file_id} not found in database")
            
            # Step 2: Extract all tables (ALL sheets, no skipping)
            extraction_result = self.extractor.extract_all_tables(file_blob)
            
            if extraction_result.get("errors"):
                result["errors"].extend(extraction_result["errors"])
            
            # Step 3: Save extraction audit
            audit = extraction_result.get("audit", {})
            result["audit"] = audit
            
            self.storage.save_extraction_audit(
                file_id=file_id,
                total_sheets=audit.get("total_sheets", 0),
                processed_sheets=audit.get("processed_sheets", 0),
                sheets_with_tables=audit.get("sheets_with_tables", 0),
                sheets_without_tables=audit.get("sheets_without_tables", []),
                total_tables=audit.get("total_tables", 0),
                warnings=audit.get("warnings", []),
                sheet_details=audit.get("sheet_details", {})
            )
            
            # Step 4: Save extracted tables to database
            for table in extraction_result.get("tables", []):
                table_type = self.extractor.detect_table_type(table.get("headers", []))
                
                # Make table data JSON-safe (convert datetime, etc.)
                safe_data = make_json_safe(table.get("data", []))
                safe_headers = make_json_safe(table.get("headers", []))
                
                saved_table = self.storage.save_extracted_table(
                    file_id=file_id,
                    sheet_name=table["sheet_name"],
                    table_index=table["table_index"],
                    headers=safe_headers,
                    table_data=safe_data,
                    detected_type=table_type
                )
                
                # Step 5: Analyze table and detect issues
                issues = self._analyze_table(saved_table.table_id, table)
                
                # Save detected issues with RULE EVIDENCE
                for issue in issues:
                    self.storage.save_detected_issue(
                        table_id=saved_table.table_id,
                        issue_type=issue["type"],
                        issue_category=issue["category"],
                        severity=issue["severity"],
                        description=issue["description"],
                        site_id=issue.get("site_id"),
                        affected_rows=issue.get("affected_rows"),
                        # RULE EVIDENCE
                        rule_id=issue.get("rule_id"),
                        trigger_condition=issue.get("trigger_condition"),
                        threshold_value=issue.get("threshold_value"),
                        actual_value=issue.get("actual_value"),
                        confidence_level=issue.get("confidence_level", "rule_verified")
                    )
            
            result["tables_extracted"] = extraction_result.get("total_tables", 0)
            
            # Step 6: Get DE-DUPLICATED issues for risk calculation
            raw_issues = self.storage.get_issues_summary(file_id)
            dedup_issues = self.storage.get_deduplicated_issues(file_id)
            
            result["issues_detected"] = raw_issues.get("total_issues", 0)
            result["unique_issues"] = dedup_issues.get("total_unique_issues", 0)
            
            # Step 7: Calculate NORMALIZED risk using de-duplicated issues
            risk_level, risk_score = self._calculate_normalized_risk(dedup_issues)
            result["risk_level"] = risk_level
            result["risk_score"] = risk_score
            
            # Step 8: Save analysis results
            self.storage.save_analysis_result(
                file_id=file_id,
                total_tables=result["tables_extracted"],
                issues_summary=dedup_issues,  # Use de-duplicated
                risk_level=risk_level,
                risk_score=risk_score
            )
            
            # Step 9: Update status to completed
            self.storage.update_file_status(file_id, ProcessingStatus.COMPLETED)
            result["success"] = True
            
        except Exception as e:
            # Rollback any pending transaction
            try:
                self.storage.session.rollback()
            except:
                pass
            
            # Try to update file status to failed
            try:
                self.storage.update_file_status(
                    file_id, ProcessingStatus.FAILED, str(e)
                )
            except:
                pass
            
            result["errors"].append(str(e))
        
        return result
    
    def _analyze_table(self, table_id: int, table: Dict) -> List[Dict]:
        """Analyze a single table and detect issues."""
        issues = []
        headers = [h.lower() for h in table.get("headers", [])]
        data = table.get("data", [])
        
        if not data:
            return issues
        
        # Standardize column names for analysis
        header_mapping = {}
        for h in headers:
            std_name = self.standardizer.standardize_column_name(h)
            header_mapping[h] = std_name
        
        # Detect data quality issues
        issues.extend(self._detect_quality_issues(headers, data, table))
        
        # Detect operational issues
        issues.extend(self._detect_operational_issues(headers, data, table))
        
        return issues
    
    def _detect_quality_issues(self, headers: List[str], data: List[Dict], table: Dict) -> List[Dict]:
        """Detect data quality issues in a table with FULL RULE EVIDENCE."""
        issues = []
        headers_text = ' '.join(headers).lower()
        row_count = len(data)
        
        if row_count == 0:
            return issues
        
        # ========== GENERIC RULE: MISSING_DATA (fires on ANY table) ==========
        total_cells = 0
        missing_cells = 0
        affected_rows = []
        
        for i, row in enumerate(data):
            for key, value in row.items():
                total_cells += 1
                if value is None or str(value).strip() == '' or str(value).lower() == 'nan':
                    missing_cells += 1
                    if i not in affected_rows:
                        affected_rows.append(i)
        
        if total_cells > 0:
            missing_pct = (missing_cells / total_cells) * 100
            
            if missing_pct > 5:  # More than 5% missing
                threshold = 30 if missing_pct > 30 else 15 if missing_pct > 15 else 5
                severity = "High" if missing_pct > 30 else "Medium" if missing_pct > 15 else "Low"
                issues.append({
                    "type": "quality",
                    "category": "missing_data",
                    "severity": severity,
                    "description": f"{missing_pct:.1f}% missing data ({missing_cells}/{total_cells} cells) in {table['sheet_name']}",
                    "affected_rows": affected_rows[:50],
                    # RULE EVIDENCE
                    "rule_id": "MISSING_DATA",
                    "trigger_condition": f"missing_percentage > {threshold}%",
                    "threshold_value": f"{threshold}%",
                    "actual_value": f"{missing_pct:.1f}%",
                    "confidence_level": "rule_verified"
                })
        
        # ========== GENERIC RULE: EMPTY_ROWS ==========
        empty_rows = 0
        for i, row in enumerate(data):
            all_empty = all(
                v is None or str(v).strip() == '' or str(v).lower() == 'nan'
                for v in row.values()
            )
            if all_empty:
                empty_rows += 1
        
        if empty_rows > 0:
            threshold = 5 if empty_rows > 5 else 1
            severity = "Medium" if empty_rows > 5 else "Low"
            issues.append({
                "type": "quality",
                "category": "empty_rows",
                "severity": severity,
                "description": f"{empty_rows} completely empty rows in {table['sheet_name']}",
                # RULE EVIDENCE
                "rule_id": "EMPTY_ROWS",
                "trigger_condition": f"empty_row_count > {threshold}",
                "threshold_value": str(threshold),
                "actual_value": str(empty_rows),
                "confidence_level": "rule_verified"
            })
        
        # ========== RULE: MISSING_LAB_DATA (specific) ==========
        if 'lab' in headers_text or 'test' in headers_text or 'result' in headers_text:
            missing_count = 0
            lab_affected = []
            
            for i, row in enumerate(data):
                for key, value in row.items():
                    if 'name' in key.lower() or 'value' in key.lower() or 'result' in key.lower():
                        if value is None or str(value).strip() == '':
                            missing_count += 1
                            lab_affected.append(i)
                            break
            
            if missing_count > 0:
                threshold = 10 if missing_count > 10 else 3 if missing_count > 3 else 1
                severity = "High" if missing_count > 10 else "Medium" if missing_count > 3 else "Low"
                issues.append({
                    "type": "quality",
                    "category": "missing_lab_data",
                    "severity": severity,
                    "description": f"{missing_count} rows with missing lab data in {table['sheet_name']}",
                    "affected_rows": lab_affected[:50],
                    # RULE EVIDENCE
                    "rule_id": "MISSING_LAB_DATA",
                    "trigger_condition": f"missing_lab_values > {threshold}",
                    "threshold_value": str(threshold),
                    "actual_value": str(missing_count),
                    "confidence_level": "rule_verified"
                })
        
        # ========== RULE: DATA_INCONSISTENCY (detect mixed types) ==========
        for header in headers[:5]:  # Check first 5 columns
            col_values = [row.get(header) for row in data if row.get(header) is not None]
            if len(col_values) > 5:
                # Check if column has mixed numeric/text
                numeric_count = sum(1 for v in col_values if str(v).replace('.', '').replace('-', '').isdigit())
                text_count = len(col_values) - numeric_count
                
                if numeric_count > 0 and text_count > 0 and min(numeric_count, text_count) > len(col_values) * 0.2:
                    issues.append({
                        "type": "quality",
                        "category": "data_inconsistency",
                        "severity": "Low",
                        "description": f"Mixed data types in column '{header[:20]}' ({numeric_count} numeric, {text_count} text)",
                        # RULE EVIDENCE
                        "rule_id": "DATA_INCONSISTENCY",
                        "trigger_condition": "mixed_types_ratio > 20%",
                        "threshold_value": "20%",
                        "actual_value": f"{min(numeric_count, text_count) / len(col_values) * 100:.0f}%",
                        "confidence_level": "rule_verified"
                    })
                    break  # Only report once per table
        
        # ========== RULE: LARGE_TABLE (informational) ==========
        if row_count > 100:
            issues.append({
                "type": "quality",
                "category": "large_dataset",
                "severity": "Low",
                "description": f"Large table with {row_count} rows in {table['sheet_name']} - review sampling recommended",
                # RULE EVIDENCE
                "rule_id": "LARGE_TABLE",
                "trigger_condition": "row_count > 100",
                "threshold_value": "100",
                "actual_value": str(row_count),
                "confidence_level": "rule_verified"
            })
        
        return issues
    
    def _detect_operational_issues(self, headers: List[str], data: List[Dict], table: Dict) -> List[Dict]:
        """Detect operational issues in a table with FULL RULE EVIDENCE."""
        issues = []
        headers_text = ' '.join(headers)
        
        # ========== RULE: QUERY_BACKLOG ==========
        if 'query' in headers_text or 'open' in headers_text:
            query_counts = {}
            for row in data:
                site_id = None
                query_count = 0
                
                for key, value in row.items():
                    key_lower = key.lower()
                    if 'site' in key_lower:
                        site_id = str(value)
                    if 'query' in key_lower or 'open' in key_lower:
                        try:
                            query_count = int(float(str(value))) if value else 0
                        except:
                            pass
                
                if site_id and query_count > 0:
                    query_counts[site_id] = query_counts.get(site_id, 0) + query_count
            
            for site_id, count in query_counts.items():
                if count > 10:
                    threshold = 50 if count > 50 else 20 if count > 20 else 10
                    severity = "High" if count > 50 else "Medium" if count > 20 else "Low"
                    issues.append({
                        "type": "operational",
                        "category": "query_backlog",
                        "severity": severity,
                        "description": f"Site {site_id}: {count} open queries",
                        "site_id": site_id,
                        # RULE EVIDENCE
                        "rule_id": "QUERY_BACKLOG",
                        "trigger_condition": f"open_queries > {threshold}",
                        "threshold_value": str(threshold),
                        "actual_value": str(count),
                        "confidence_level": "rule_verified"
                    })
        
        # ========== RULE: DELAYED_VISITS ==========
        if 'delay' in headers_text or 'overdue' in headers_text or 'visit' in headers_text:
            delayed_count = sum(1 for row in data for k, v in row.items()
                               if ('delay' in str(v).lower() or 'overdue' in str(v).lower()))
            
            if delayed_count > 0:
                threshold = 10 if delayed_count > 10 else 3 if delayed_count > 3 else 1
                severity = "High" if delayed_count > 10 else "Medium" if delayed_count > 3 else "Low"
                issues.append({
                    "type": "operational",
                    "category": "delayed_visits",
                    "severity": severity,
                    "description": f"{delayed_count} delayed/overdue visits in {table['sheet_name']}",
                    # RULE EVIDENCE
                    "rule_id": "DELAYED_VISITS",
                    "trigger_condition": f"delayed_count > {threshold}",
                    "threshold_value": str(threshold),
                    "actual_value": str(delayed_count),
                    "confidence_level": "rule_verified"
                })
        
        return issues
    
    def _calculate_risk(self, issues_summary: Dict) -> tuple:
        """Calculate risk level and score based on issues."""
        by_severity = issues_summary.get("by_severity", {})
        high = by_severity.get("High", 0)
        medium = by_severity.get("Medium", 0)
        low = by_severity.get("Low", 0)
        
        # Weighted score
        risk_score = (high * 3) + (medium * 1.5) + (low * 0.5)
        
        # Determine level
        if high > 3 or risk_score > 15:
            risk_level = "High Risk"
        elif high > 0 or medium > 5 or risk_score > 5:
            risk_level = "Medium Risk"
        else:
            risk_level = "Low Risk"
        
        return risk_level, risk_score
    
    def _calculate_normalized_risk(self, dedup_issues: Dict) -> tuple:
        """
        Calculate NORMALIZED risk using de-duplicated issues with capped contribution.
        
        - Uses unique issues (de-duplicated by Site+Type)
        - Caps contribution per issue category at MAX_CONTRIBUTION
        - Prevents repeated tables from inflating risk
        """
        MAX_CONTRIBUTION_PER_TYPE = 5.0  # Cap at 5 points per issue category
        SEVERITY_WEIGHTS = {"High": 3.0, "Medium": 1.5, "Low": 0.5}
        
        issues = dedup_issues.get("issues", [])
        
        # Group risk contribution by category (capped)
        risk_by_category = {}
        
        for issue in issues:
            category = issue.get("issue_category", "unknown")
            severity = issue.get("severity", "Low")
            weight = SEVERITY_WEIGHTS.get(severity, 0.5)
            
            current = risk_by_category.get(category, 0)
            # Cap contribution per category
            risk_by_category[category] = min(current + weight, MAX_CONTRIBUTION_PER_TYPE)
        
        # Total risk score (sum of capped category scores)
        total_risk_score = sum(risk_by_category.values())
        
        # Count by severity for level determination
        by_severity = dedup_issues.get("by_severity", {})
        high = by_severity.get("High", 0)
        medium = by_severity.get("Medium", 0)
        
        # Determine level
        if high >= 3 or total_risk_score >= 12:
            risk_level = "High Risk"
        elif high > 0 or medium >= 3 or total_risk_score >= 5:
            risk_level = "Medium Risk"
        else:
            risk_level = "Low Risk"
        
        return risk_level, round(total_risk_score, 2)
    
    def generate_insights(self, file_id: int) -> Dict:
        """Generate AI insights for a processed file."""
        analysis = self.storage.get_analysis_by_file(file_id)
        if not analysis:
            return {"error": "No analysis found for this file"}
        
        tables_summary = self.storage.get_tables_summary(file_id)
        issues_summary = self.storage.get_issues_summary(file_id)
        
        # Build analytics JSON for Gemini (NO raw Excel data)
        analytics_json = {
            "file_id": file_id,
            "total_tables": tables_summary.get("total_tables", 0),
            "total_sheets": tables_summary.get("total_sheets", 0),
            "table_types": tables_summary.get("by_type", {}),
            "risk_level": analysis.risk_level,
            "risk_score": analysis.risk_score,
            "issues_summary": issues_summary
        }
        
        # Generate insights
        summary_insight = self.gemini.generate_insight(analytics_json, "summary")
        
        # Save insight for audit trail
        self.storage.save_gemini_insight(
            prompt_type="summary",
            input_json=analytics_json,
            output_text=summary_insight.get("insight", ""),
            file_id=file_id
        )
        
        return {
            "summary": summary_insight,
            "analytics": analytics_json
        }
    
    def get_full_analysis(self, file_id: int) -> Dict:
        """Get complete analysis with full traceability."""
        file_record = self.storage.get_file_by_id(file_id)
        if not file_record:
            return {"error": "File not found"}
        
        # Get extraction audit
        audit = self.storage.get_extraction_audit(file_id)
        
        return {
            "file": file_record.to_dict(),
            "tables": self.storage.get_tables_summary(file_id),
            "issues": self.storage.get_deduplicated_issues(file_id),  # Use de-duplicated
            "analysis": self.storage.get_analysis_by_file(file_id).to_dict() if self.storage.get_analysis_by_file(file_id) else None,
            "insights": [i.to_dict() for i in self.storage.get_insights_by_file(file_id)],
            "audit": audit.to_dict() if audit else None
        }
    
    # ==================== STUDY-LEVEL ANALYTICS ====================
    
    def analyze_study(self, study_id: int) -> Dict:
        """
        Analyze entire study with cross-file de-duplication.
        This is the PRIMARY analytics method for enterprise use.
        """
        result = {
            "study_id": study_id,
            "success": False,
            "total_files": 0,
            "total_issues": 0,
            "unique_issues": 0,
            "risk_level": None,
            "risk_score": 0.0,
            "errors": []
        }
        
        try:
            study = self.storage.get_study_by_id(study_id)
            if not study:
                result["errors"].append("Study not found")
                return result
            
            # Get all files in study
            files = self.storage.get_study_files(study_id)
            result["total_files"] = len(files)
            
            # Get study-level de-duplicated issues
            dedup_issues = self.storage.get_study_deduplicated_issues(study_id)
            result["total_issues"] = dedup_issues.get("total_raw_issues", 0)
            result["unique_issues"] = dedup_issues.get("total_unique_issues", 0)
            
            # Calculate STUDY-level risk (not file-level)
            risk_level, risk_score = self._calculate_normalized_risk(dedup_issues)
            result["risk_level"] = risk_level
            result["risk_score"] = risk_score
            
            # Update study record
            self.storage.update_study_analytics(
                study_id=study_id,
                total_issues=result["total_issues"],
                unique_issues=result["unique_issues"],
                risk_level=risk_level,
                risk_score=risk_score
            )
            
            # TRIGGER ALERTS based on thresholds
            self.storage.trigger_alerts_for_issues(study_id, dedup_issues)
            
            # SAVE TREND SNAPSHOT for historical tracking
            self.storage.save_risk_snapshot(
                study_id=study_id,
                risk_score=risk_score,
                risk_level=risk_level,
                total_issues=result["total_issues"],
                unique_issues=result["unique_issues"],
                total_files=result["total_files"]
            )
            
            result["success"] = True
            
        except Exception as e:
            result["errors"].append(str(e))
        
        return result
    
    def generate_study_insights(self, study_id: int) -> Dict:
        """
        Generate AI insights at STUDY level.
        Gemini receives study-level aggregated JSON only.
        """
        study_summary = self.storage.get_study_summary(study_id)
        
        if "error" in study_summary:
            return study_summary
        
        # Build study-level prompt for Gemini
        study_json = {
            "study_name": study_summary["study"]["study_name"],
            "total_files": study_summary["files"]["total"],
            "total_tables": study_summary["extraction"]["total_tables"],
            "unique_issues": study_summary["issues"]["total_unique_issues"],
            "sites_affected": study_summary["issues"]["sites_affected"],
            "risk_level": study_summary["risk"]["level"],
            "risk_score": study_summary["risk"]["score"],
            "issues_by_severity": study_summary["issues"]["by_severity"],
            "issues_by_category": study_summary["issues"]["by_category"]
        }
        
        # Generate study insight
        prompt = f"""
        Analyze this clinical trial STUDY (not a single file):
        
        Study: {study_json['study_name']}
        Files Analyzed: {study_json['total_files']}
        Tables Extracted: {study_json['total_tables']}
        Unique Issues (de-duplicated): {study_json['unique_issues']}
        Sites Affected: {study_json['sites_affected']}
        Risk Level: {study_json['risk_level']} (Score: {study_json['risk_score']})
        
        Issues by Severity: {study_json['issues_by_severity']}
        Issues by Category: {study_json['issues_by_category']}
        
        Questions to answer:
        1. Why is this study at {study_json['risk_level']}?
        2. Which issue categories are driving study risk?
        3. Are issues systemic (many sites) or isolated (few sites)?
        4. What immediate actions should be taken?
        """
        
        insight_result = self.gemini.generate_insight(study_json, "study_insight")
        insight_text = insight_result.get("insight", "") if isinstance(insight_result, dict) else str(insight_result)
        
        # Save insight (linked to study via first file if exists)
        files = self.storage.get_study_files(study_id)
        file_id = files[0].file_id if files else None
        
        self.storage.save_gemini_insight(
            prompt_type="study_insight",
            input_json=study_json,
            output_text=insight_text,
            file_id=file_id
        )
        
        return {
            "study_id": study_id,
            "insight": insight_text,
            "analytics": study_json
        }
    
    def get_study_full_analysis(self, study_id: int) -> Dict:
        """Get complete study-level analysis for UI."""
        study = self.storage.get_study_by_id(study_id)
        if not study:
            return {"error": "Study not found"}
        
        summary = self.storage.get_study_summary(study_id)
        
        return {
            "study": study.to_dict(),
            "files": summary.get("files", {}),
            "extraction": summary.get("extraction", {}),
            "issues": summary.get("issues", {}),
            "risk": summary.get("risk", {}),
            "insights": []  # Study insights retrieved separately
        }

