"""
Database Storage - CRUD operations for the clinical trial system
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import io
from sqlalchemy.orm import Session

from .models import (
    Study, UploadedFile, ExtractedTable, DetectedIssue, 
    AnalysisResult, GeminiInsight, ExtractionAudit, Alert, RiskTrendSnapshot, ProcessingStatus, AnalysisStatus,
    get_engine, init_database, get_session
)


class DatabaseStorage:
    """Handles all database operations for the clinical trial system."""
    
    def __init__(self, db_path: str = "database/clinical_trials.db"):
        self.db_path = db_path
        self.engine = init_database(db_path)
        self._session = None
    
    @property
    def session(self) -> Session:
        """Get or create session."""
        if self._session is None:
            self._session = get_session(self.engine)
        return self._session
    
    def close(self):
        """Close session."""
        if self._session:
            self._session.close()
            self._session = None
    
    # ==================== FILE OPERATIONS ====================
    
    def save_uploaded_file(self, filename: str, file_bytes: bytes, 
                          user_id: str = "default_user") -> UploadedFile:
        """Store an uploaded file in the database."""
        file_record = UploadedFile(
            user_id=user_id,
            filename=filename,
            file_blob=file_bytes,
            file_size=len(file_bytes),
            upload_timestamp=datetime.utcnow(),
            processing_status=ProcessingStatus.PENDING.value
        )
        self.session.add(file_record)
        self.session.commit()
        return file_record
    
    def get_file_by_id(self, file_id: int) -> Optional[UploadedFile]:
        """Retrieve a file by ID."""
        return self.session.query(UploadedFile).filter_by(file_id=file_id).first()
    
    def get_file_blob(self, file_id: int) -> Optional[io.BytesIO]:
        """Get file content as BytesIO for processing."""
        file_record = self.get_file_by_id(file_id)
        if file_record and file_record.file_blob:
            return io.BytesIO(file_record.file_blob)
        return None
    
    def get_all_files(self, user_id: Optional[str] = None) -> List[UploadedFile]:
        """Get all uploaded files, optionally filtered by user."""
        query = self.session.query(UploadedFile)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.order_by(UploadedFile.upload_timestamp.desc()).all()
    
    def update_file_status(self, file_id: int, status: ProcessingStatus, 
                          error_message: Optional[str] = None) -> None:
        """Update file processing status."""
        file_record = self.get_file_by_id(file_id)
        if file_record:
            file_record.processing_status = status.value
            if error_message:
                file_record.error_message = error_message
            self.session.commit()
    
    def delete_file(self, file_id: int) -> bool:
        """Delete a file and all related data."""
        file_record = self.get_file_by_id(file_id)
        if file_record:
            self.session.delete(file_record)
            self.session.commit()
            return True
        return False
    
    # ==================== TABLE OPERATIONS ====================
    
    def save_extracted_table(self, file_id: int, sheet_name: str, table_index: int,
                            headers: List[str], table_data: List[Dict],
                            detected_type: Optional[str] = None) -> ExtractedTable:
        """Save an extracted table."""
        table_record = ExtractedTable(
            file_id=file_id,
            sheet_name=sheet_name,
            table_index=table_index,
            headers=headers,
            row_count=len(table_data),
            column_count=len(headers) if headers else 0,
            table_data=table_data,
            detected_type=detected_type,
            extraction_timestamp=datetime.utcnow()
        )
        self.session.add(table_record)
        self.session.commit()
        return table_record
    
    def get_tables_by_file(self, file_id: int) -> List[ExtractedTable]:
        """Get all extracted tables for a file."""
        return self.session.query(ExtractedTable).filter_by(file_id=file_id).all()
    
    def get_table_by_id(self, table_id: int) -> Optional[ExtractedTable]:
        """Get a specific table by ID."""
        return self.session.query(ExtractedTable).filter_by(table_id=table_id).first()
    
    def get_tables_summary(self, file_id: int) -> Dict:
        """Get summary of tables for a file."""
        tables = self.get_tables_by_file(file_id)
        by_sheet = {}
        by_type = {}
        
        for table in tables:
            # Group by sheet
            if table.sheet_name not in by_sheet:
                by_sheet[table.sheet_name] = []
            by_sheet[table.sheet_name].append(table.to_dict())
            
            # Group by type
            table_type = table.detected_type or "Unknown"
            by_type[table_type] = by_type.get(table_type, 0) + 1
        
        return {
            "total_tables": len(tables),
            "total_sheets": len(by_sheet),
            "by_sheet": by_sheet,
            "by_type": by_type
        }
    
    # ==================== ISSUE OPERATIONS ====================
    
    def save_detected_issue(self, table_id: int, issue_type: str, issue_category: str,
                           severity: str, description: str, site_id: Optional[str] = None,
                           affected_rows: Optional[List[int]] = None,
                           rule_id: Optional[str] = None,
                           trigger_condition: Optional[str] = None,
                           threshold_value: Optional[str] = None,
                           actual_value: Optional[str] = None,
                           confidence_level: str = "rule_verified") -> DetectedIssue:
        """Save a detected issue with full rule evidence."""
        issue_record = DetectedIssue(
            table_id=table_id,
            issue_type=issue_type,
            issue_category=issue_category,
            severity=severity,
            description=description,
            site_id=site_id,
            affected_rows=affected_rows,
            detection_timestamp=datetime.utcnow(),
            # RULE EVIDENCE
            rule_id=rule_id,
            trigger_condition=trigger_condition,
            threshold_value=threshold_value,
            actual_value=actual_value,
            confidence_level=confidence_level
        )
        self.session.add(issue_record)
        self.session.commit()
        return issue_record
    
    def get_issues_by_file(self, file_id: int) -> List[DetectedIssue]:
        """Get all issues for a file with full traceability."""
        tables = self.get_tables_by_file(file_id)
        table_ids = [t.table_id for t in tables]
        if not table_ids:
            return []
        return self.session.query(DetectedIssue).filter(
            DetectedIssue.table_id.in_(table_ids)
        ).all()
    
    def get_issues_by_table(self, table_id: int) -> List[DetectedIssue]:
        """Get issues for a specific table."""
        return self.session.query(DetectedIssue).filter_by(table_id=table_id).all()
    
    def get_issues_summary(self, file_id: int) -> Dict:
        """Get issues summary with traceability."""
        issues = self.get_issues_by_file(file_id)
        
        by_severity = {"High": 0, "Medium": 0, "Low": 0}
        by_type = {"quality": 0, "operational": 0}
        by_category = {}
        
        for issue in issues:
            by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
            by_category[issue.issue_category] = by_category.get(issue.issue_category, 0) + 1
        
        return {
            "total_issues": len(issues),
            "by_severity": by_severity,
            "by_type": by_type,
            "by_category": by_category,
            "issues": [issue.to_dict() for issue in issues]
        }
    
    # ==================== ANALYSIS OPERATIONS ====================
    
    def save_analysis_result(self, file_id: int, total_tables: int, issues_summary: Dict,
                            risk_level: str, risk_score: float) -> AnalysisResult:
        """Save aggregated analysis results."""
        result = AnalysisResult(
            file_id=file_id,
            total_tables=total_tables,
            total_issues=issues_summary.get("total_issues", 0),
            high_severity_count=issues_summary.get("by_severity", {}).get("High", 0),
            medium_severity_count=issues_summary.get("by_severity", {}).get("Medium", 0),
            low_severity_count=issues_summary.get("by_severity", {}).get("Low", 0),
            risk_level=risk_level,
            risk_score=risk_score,
            quality_issues_json=issues_summary.get("by_type", {}).get("quality"),
            operational_issues_json=issues_summary.get("by_type", {}).get("operational"),
            analysis_timestamp=datetime.utcnow()
        )
        self.session.add(result)
        self.session.commit()
        return result
    
    def get_analysis_by_file(self, file_id: int) -> Optional[AnalysisResult]:
        """Get latest analysis result for a file."""
        return self.session.query(AnalysisResult).filter_by(
            file_id=file_id
        ).order_by(AnalysisResult.analysis_timestamp.desc()).first()
    
    # ==================== GEMINI INSIGHT OPERATIONS ====================
    
    def save_gemini_insight(self, prompt_type: str, input_json: Dict, 
                           output_text: str, file_id: Optional[int] = None) -> GeminiInsight:
        """Save AI-generated insight for audit trail."""
        insight = GeminiInsight(
            file_id=file_id,
            prompt_type=prompt_type,
            input_json=input_json,
            output_text=output_text,
            generation_timestamp=datetime.utcnow()
        )
        self.session.add(insight)
        self.session.commit()
        return insight
    
    def get_insights_by_file(self, file_id: int) -> List[GeminiInsight]:
        """Get all AI insights for a file."""
        return self.session.query(GeminiInsight).filter_by(
            file_id=file_id
        ).order_by(GeminiInsight.generation_timestamp.desc()).all()
    
    # ==================== AGGREGATE OPERATIONS ====================
    
    def get_system_summary(self) -> Dict:
        """Get overall system summary."""
        total_files = self.session.query(UploadedFile).count()
        total_tables = self.session.query(ExtractedTable).count()
        total_issues = self.session.query(DetectedIssue).count()
        
        pending = self.session.query(UploadedFile).filter_by(
            processing_status=ProcessingStatus.PENDING.value
        ).count()
        completed = self.session.query(UploadedFile).filter_by(
            processing_status=ProcessingStatus.COMPLETED.value
        ).count()
        
        return {
            "total_files": total_files,
            "total_tables": total_tables,
            "total_issues": total_issues,
            "pending_files": pending,
            "completed_files": completed
        }
    
    # ==================== EXTRACTION AUDIT OPERATIONS ====================
    
    def save_extraction_audit(self, file_id: int, total_sheets: int, 
                              processed_sheets: int, sheets_with_tables: int,
                              sheets_without_tables: List[str], total_tables: int,
                              warnings: List[str], sheet_details: Dict) -> ExtractionAudit:
        """Save extraction audit for sheet completeness validation."""
        audit = ExtractionAudit(
            file_id=file_id,
            total_sheets=total_sheets,
            processed_sheets=processed_sheets,
            sheets_with_tables=sheets_with_tables,
            sheets_without_tables=sheets_without_tables,
            total_tables=total_tables,
            warnings=warnings,
            sheet_details=sheet_details,
            audit_timestamp=datetime.utcnow()
        )
        self.session.add(audit)
        self.session.commit()
        return audit
    
    def get_extraction_audit(self, file_id: int) -> Optional[ExtractionAudit]:
        """Get extraction audit for a file."""
        return self.session.query(ExtractionAudit).filter_by(
            file_id=file_id
        ).order_by(ExtractionAudit.audit_timestamp.desc()).first()
    
    # ==================== DE-DUPLICATED ISSUES ====================
    
    def get_deduplicated_issues(self, file_id: int) -> Dict:
        """Get de-duplicated issues by Site ID + Issue Category."""
        issues = self.get_issues_by_file(file_id)
        
        # De-duplicate by (site_id, issue_category)
        seen = {}
        severity_priority = {"High": 3, "Medium": 2, "Low": 1}
        
        for issue in issues:
            key = (issue.site_id or "unknown", issue.issue_category)
            priority = severity_priority.get(issue.severity, 0)
            
            if key not in seen or priority > seen[key]["priority"]:
                seen[key] = {
                    "issue": issue.to_dict(),
                    "priority": priority
                }
        
        deduplicated = [v["issue"] for v in seen.values()]
        
        # Count by severity (de-duplicated)
        by_severity = {"High": 0, "Medium": 0, "Low": 0}
        by_type = {"quality": 0, "operational": 0}
        by_category = {}
        
        for issue in deduplicated:
            by_severity[issue["severity"]] = by_severity.get(issue["severity"], 0) + 1
            by_type[issue["issue_type"]] = by_type.get(issue["issue_type"], 0) + 1
            by_category[issue["issue_category"]] = by_category.get(issue["issue_category"], 0) + 1
        
        return {
            "total_unique_issues": len(deduplicated),
            "total_raw_issues": len(issues),
            "deduplication_ratio": len(deduplicated) / len(issues) if issues else 1.0,
            "by_severity": by_severity,
            "by_type": by_type,
            "by_category": by_category,
            "issues": deduplicated
        }
    
    # ==================== STUDY OPERATIONS ====================
    
    def create_study(self, study_name: str, description: str = None) -> Study:
        """Create a new study."""
        study = Study(
            study_name=study_name,
            description=description,
            created_at=datetime.utcnow()
        )
        self.session.add(study)
        self.session.commit()
        return study
    
    def get_study_by_id(self, study_id: int) -> Optional[Study]:
        """Get study by ID."""
        return self.session.query(Study).filter_by(study_id=study_id).first()
    
    def get_study_by_name(self, study_name: str) -> Optional[Study]:
        """Get study by name."""
        return self.session.query(Study).filter_by(study_name=study_name).first()
    
    def get_or_create_study(self, study_name: str) -> Study:
        """Get existing study or create new one."""
        study = self.get_study_by_name(study_name)
        if not study:
            study = self.create_study(study_name)
        return study
    
    def get_all_studies(self) -> List[Study]:
        """Get all studies."""
        return self.session.query(Study).order_by(Study.created_at.desc()).all()
    
    def get_study_files(self, study_id: int) -> List[UploadedFile]:
        """Get all files for a study."""
        return self.session.query(UploadedFile).filter_by(study_id=study_id).all()
    
    def assign_file_to_study(self, file_id: int, study_id: int) -> None:
        """Assign a file to a study."""
        file_record = self.get_file_by_id(file_id)
        if file_record:
            file_record.study_id = study_id
            self.session.commit()
    
    # ==================== STUDY-LEVEL AGGREGATION ====================
    
    def get_study_issues(self, study_id: int) -> List[DetectedIssue]:
        """Get ALL issues from all files in a study."""
        files = self.get_study_files(study_id)
        all_issues = []
        
        for file in files:
            file_issues = self.get_issues_by_file(file.file_id)
            all_issues.extend(file_issues)
        
        return all_issues
    
    def get_study_deduplicated_issues(self, study_id: int) -> Dict:
        """
        Get STUDY-LEVEL de-duplicated issues.
        De-duplicates across ALL files in the study by (Site ID + Issue Type).
        Prevents multi-file risk inflation.
        """
        all_issues = self.get_study_issues(study_id)
        
        # De-duplicate by (study_id, site_id, issue_category)
        seen = {}
        severity_priority = {"High": 3, "Medium": 2, "Low": 1}
        
        for issue in all_issues:
            # Key includes study context
            key = (study_id, issue.site_id or "unknown", issue.issue_category)
            priority = severity_priority.get(issue.severity, 0)
            
            if key not in seen or priority > seen[key]["priority"]:
                seen[key] = {
                    "issue": issue.to_dict(),
                    "priority": priority,
                    "file_id": issue.table.file_id if issue.table else None
                }
        
        deduplicated = [v["issue"] for v in seen.values()]
        
        # Count by severity (study-level)
        by_severity = {"High": 0, "Medium": 0, "Low": 0}
        by_type = {"quality": 0, "operational": 0}
        by_category = {}
        sites_affected = set()
        
        for issue in deduplicated:
            by_severity[issue["severity"]] = by_severity.get(issue["severity"], 0) + 1
            by_type[issue["issue_type"]] = by_type.get(issue["issue_type"], 0) + 1
            by_category[issue["issue_category"]] = by_category.get(issue["issue_category"], 0) + 1
            if issue.get("site_id"):
                sites_affected.add(issue["site_id"])
        
        return {
            "study_id": study_id,
            "total_unique_issues": len(deduplicated),
            "total_raw_issues": len(all_issues),
            "deduplication_ratio": len(deduplicated) / len(all_issues) if all_issues else 1.0,
            "sites_affected": len(sites_affected),
            "by_severity": by_severity,
            "by_type": by_type,
            "by_category": by_category,
            "issues": deduplicated
        }
    
    def update_study_analytics(self, study_id: int, total_issues: int, 
                               unique_issues: int, risk_level: str, 
                               risk_score: float, cached_analytics: Dict = None) -> None:
        """Update study-level analytics and cache."""
        study = self.get_study_by_id(study_id)
        if study:
            study.total_issues = total_issues
            study.unique_issues = unique_issues
            study.risk_level = risk_level
            study.risk_score = risk_score
            study.updated_at = datetime.utcnow()
            if cached_analytics:
                study.cached_analytics = cached_analytics
                study.cached_risk_score = risk_score
            self.session.commit()
    
    def update_study_status(self, study_id: int, status: str, progress: int = 0) -> None:
        """Update study analysis status and progress."""
        study = self.get_study_by_id(study_id)
        if study:
            study.analysis_status = status
            study.analysis_progress = progress
            if status == AnalysisStatus.COMPLETED.value:
                study.last_analyzed_at = datetime.utcnow()
            self.session.commit()
    
    def get_study_summary(self, study_id: int) -> Dict:
        """Get comprehensive study summary for Gemini AI."""
        study = self.get_study_by_id(study_id)
        if not study:
            return {"error": "Study not found"}
        
        files = self.get_study_files(study_id)
        dedup_issues = self.get_study_deduplicated_issues(study_id)
        
        # Aggregate file info
        total_tables = 0
        total_sheets = 0
        for file in files:
            tables = self.get_tables_by_file(file.file_id)
            total_tables += len(tables)
            sheets = set(t.sheet_name for t in tables)
            total_sheets += len(sheets)
        
        return {
            "study": study.to_dict(),
            "files": {
                "total": len(files),
                "list": [f.to_dict() for f in files]
            },
            "extraction": {
                "total_tables": total_tables,
                "total_sheets": total_sheets
            },
            "issues": dedup_issues,
            "risk": {
                "level": study.risk_level,
                "score": study.risk_score
            }
        }
    
    # ==================== ALERT OPERATIONS ====================
    
    def create_alert(self, alert_type: str, severity: str, title: str, message: str,
                    study_id: int = None, file_id: int = None, rule_id: str = None,
                    threshold_value: str = None, actual_value: str = None,
                    target_role: str = None) -> Alert:
        """Create a new alert."""
        alert = Alert(
            study_id=study_id,
            file_id=file_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            rule_id=rule_id,
            threshold_value=threshold_value,
            actual_value=actual_value,
            status="active",
            target_role=target_role
        )
        self.session.add(alert)
        self.session.commit()
        return alert
    
    def get_active_alerts(self, study_id: int = None) -> List[Alert]:
        """Get all active alerts, optionally filtered by study."""
        query = self.session.query(Alert).filter(Alert.status == "active")
        if study_id:
            query = query.filter(Alert.study_id == study_id)
        return query.order_by(Alert.created_at.desc()).all()
    
    def get_alerts_for_role(self, role: str, study_id: int = None) -> List[Alert]:
        """Get active alerts for a specific role."""
        query = self.session.query(Alert).filter(
            Alert.status == "active",
            (Alert.target_role == role) | (Alert.target_role == None)
        )
        if study_id:
            query = query.filter(Alert.study_id == study_id)
        return query.order_by(Alert.created_at.desc()).all()
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = "user") -> Alert:
        """Acknowledge an alert."""
        alert = self.session.query(Alert).filter_by(alert_id=alert_id).first()
        if alert:
            alert.status = "acknowledged"
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            self.session.commit()
        return alert
    
    def dismiss_alert(self, alert_id: int) -> Alert:
        """Dismiss an alert."""
        alert = self.session.query(Alert).filter_by(alert_id=alert_id).first()
        if alert:
            alert.status = "dismissed"
            self.session.commit()
        return alert
    
    def get_alerts_summary(self, study_id: int = None) -> Dict:
        """Get alerts summary count by severity."""
        alerts = self.get_active_alerts(study_id)
        return {
            "total": len(alerts),
            "critical": sum(1 for a in alerts if a.severity == "critical"),
            "warning": sum(1 for a in alerts if a.severity == "warning"),
            "info": sum(1 for a in alerts if a.severity == "info"),
            "alerts": [a.to_dict() for a in alerts[:10]]  # Top 10
        }
    
    def trigger_alerts_for_issues(self, study_id: int, issues_info: Dict):
        """Auto-trigger alerts based on issue thresholds."""
        high_count = issues_info.get("by_severity", {}).get("High", 0)
        total_issues = issues_info.get("total_unique_issues", 0)
        
        # Critical alert for multiple high-severity issues
        if high_count >= 3:
            existing = self.session.query(Alert).filter(
                Alert.study_id == study_id,
                Alert.alert_type == "high_risk",
                Alert.status == "active"
            ).first()
            
            if not existing:
                self.create_alert(
                    alert_type="high_risk",
                    severity="critical",
                    title=f"🔴 High Risk Alert: {high_count} Critical Issues",
                    message=f"Study has {high_count} high-severity issues requiring immediate attention.",
                    study_id=study_id,
                    rule_id="HIGH_RISK_THRESHOLD",
                    threshold_value="3",
                    actual_value=str(high_count),
                    target_role="CTT"
                )
        
        # Warning alert for elevated issue count
        if total_issues >= 10:
            existing = self.session.query(Alert).filter(
                Alert.study_id == study_id,
                Alert.alert_type == "threshold_breach",
                Alert.status == "active"
            ).first()
            
            if not existing:
                self.create_alert(
                    alert_type="threshold_breach",
                    severity="warning",
                    title=f"⚠️ Elevated Issues: {total_issues} Total",
                    message=f"Study has {total_issues} unique issues. Review recommended.",
                    study_id=study_id,
                    rule_id="ISSUE_COUNT_THRESHOLD",
                    threshold_value="10",
                    actual_value=str(total_issues)
                )
    
    # ==================== TREND TRACKING OPERATIONS ====================
    
    def save_risk_snapshot(self, study_id: int, risk_score: float, risk_level: str,
                          total_issues: int, unique_issues: int, total_files: int) -> RiskTrendSnapshot:
        """Save a risk score snapshot for trend tracking."""
        # Get previous snapshot for delta calculation
        previous = self.session.query(RiskTrendSnapshot).filter(
            RiskTrendSnapshot.study_id == study_id
        ).order_by(RiskTrendSnapshot.snapshot_time.desc()).first()
        
        previous_score = previous.risk_score if previous else None
        score_delta = (risk_score - previous_score) if previous_score is not None else None
        
        snapshot = RiskTrendSnapshot(
            study_id=study_id,
            risk_score=risk_score,
            risk_level=risk_level,
            total_issues=total_issues,
            unique_issues=unique_issues,
            total_files=total_files,
            previous_score=previous_score,
            score_delta=score_delta
        )
        self.session.add(snapshot)
        self.session.commit()
        return snapshot
    
    def get_risk_trend(self, study_id: int, limit: int = 10) -> List[Dict]:
        """Get risk score history for trend analysis."""
        snapshots = self.session.query(RiskTrendSnapshot).filter(
            RiskTrendSnapshot.study_id == study_id
        ).order_by(RiskTrendSnapshot.snapshot_time.desc()).limit(limit).all()
        
        # Reverse to show oldest first (for charting)
        return [s.to_dict() for s in reversed(snapshots)]
    
    def get_latest_trend(self, study_id: int) -> Dict:
        """Get the most recent trend snapshot with delta info."""
        snapshot = self.session.query(RiskTrendSnapshot).filter(
            RiskTrendSnapshot.study_id == study_id
        ).order_by(RiskTrendSnapshot.snapshot_time.desc()).first()
        
        if not snapshot:
            return {"trend": "stable", "delta": 0}
        
        return {
            "trend": snapshot.to_dict()["trend"],
            "delta": snapshot.score_delta or 0,
            "previous_score": snapshot.previous_score,
            "current_score": snapshot.risk_score,
            "snapshot_time": snapshot.snapshot_time
        }
