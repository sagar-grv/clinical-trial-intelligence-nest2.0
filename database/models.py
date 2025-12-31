"""
Database Models - SQLAlchemy models for enterprise clinical trial system
"""
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, DateTime, Text, ForeignKey, JSON, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()


class ProcessingStatus(enum.Enum):
    """File processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStatus(enum.Enum):
    """Study analysis status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Study(Base):
    """Represents a clinical trial study containing multiple files."""
    __tablename__ = 'studies'
    
    study_id = Column(Integer, primary_key=True, autoincrement=True)
    study_name = Column(String(255), nullable=False)  # From folder name or user input
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Study-level analytics
    total_files = Column(Integer, default=0)
    total_issues = Column(Integer, default=0)
    unique_issues = Column(Integer, default=0)
    risk_level = Column(String(20), nullable=True)
    risk_score = Column(Float, default=0.0)

    # Async Analysis & Caching
    analysis_status = Column(String(20), default=AnalysisStatus.PENDING.value)
    analysis_progress = Column(Integer, default=0)
    last_analyzed_at = Column(DateTime, nullable=True)
    cached_analytics = Column(JSON, nullable=True)  # Stores full analysis JSON
    cached_risk_score = Column(Float, default=0.0)
    
    # Relationships
    files = relationship("UploadedFile", back_populates="study", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "study_id": self.study_id,
            "study_name": self.study_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "total_files": len(self.files) if self.files else 0,
            "total_issues": self.total_issues,
            "unique_issues": self.unique_issues,
            "risk_level": self.risk_level,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "analysis_status": self.analysis_status,
            "analysis_progress": self.analysis_progress,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None
        }


class UploadedFile(Base):
    """Stores uploaded Excel files as BLOBs with metadata."""
    __tablename__ = 'uploaded_files'
    
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(Integer, ForeignKey('studies.study_id'), nullable=True)  # Link to study
    user_id = Column(String(100), nullable=False, default="default_user")
    filename = Column(String(255), nullable=False)
    file_blob = Column(LargeBinary, nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(20), default=ProcessingStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    study = relationship("Study", back_populates="files")
    extracted_tables = relationship("ExtractedTable", back_populates="file", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="file", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "file_id": self.file_id,
            "study_id": self.study_id,
            "study_name": self.study.study_name if self.study else None,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "processing_status": self.processing_status,
            "table_count": len(self.extracted_tables) if self.extracted_tables else 0
        }


class ExtractedTable(Base):
    """Stores extracted tables from Excel files with full traceability."""
    __tablename__ = 'extracted_tables'
    
    table_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.file_id'), nullable=False)
    sheet_name = Column(String(100), nullable=False)
    table_index = Column(Integer, nullable=False)  # 0-based index within sheet
    headers = Column(JSON, nullable=True)  # List of column headers
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    table_data = Column(JSON, nullable=True)  # Serialized table data
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)
    detected_type = Column(String(50), nullable=True)  # Clinical, Safety, etc.
    
    # Relationships
    file = relationship("UploadedFile", back_populates="extracted_tables")
    issues = relationship("DetectedIssue", back_populates="table", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "table_id": self.table_id,
            "file_id": self.file_id,
            "sheet_name": self.sheet_name,
            "table_index": self.table_index,
            "headers": self.headers,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "detected_type": self.detected_type,
            "extraction_timestamp": self.extraction_timestamp.isoformat() if self.extraction_timestamp else None
        }


class DetectedIssue(Base):
    """Stores detected data quality and operational issues with full traceability and rule evidence."""
    __tablename__ = 'detected_issues'
    
    issue_id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey('extracted_tables.table_id'), nullable=False)
    issue_type = Column(String(50), nullable=False)  # quality, operational
    issue_category = Column(String(100), nullable=False)  # missing_lab, delayed_visit, etc.
    severity = Column(String(20), nullable=False)  # Low, Medium, High
    description = Column(Text, nullable=False)
    affected_rows = Column(JSON, nullable=True)  # List of affected row indices
    site_id = Column(String(50), nullable=True)
    detection_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # ========== RULE EVIDENCE (PROOF LAYER) ==========
    rule_id = Column(String(50), nullable=True)  # e.g., QUERY_BACKLOG_HIGH
    trigger_condition = Column(String(200), nullable=True)  # e.g., "open_queries > 100"
    threshold_value = Column(String(50), nullable=True)  # e.g., "100"
    actual_value = Column(String(50), nullable=True)  # e.g., "156"
    confidence_level = Column(String(20), default="rule_verified")  # rule_verified, ai_explained, needs_review
    
    # Relationships
    table = relationship("ExtractedTable", back_populates="issues")
    
    def to_dict(self):
        return {
            "issue_id": self.issue_id,
            "table_id": self.table_id,
            "issue_type": self.issue_type,
            "issue_category": self.issue_category,
            "severity": self.severity,
            "description": self.description,
            "site_id": self.site_id,
            "file_id": self.table.file_id if self.table else None,
            "sheet_name": self.table.sheet_name if self.table else None,
            # Rule Evidence
            "rule_id": self.rule_id,
            "trigger_condition": self.trigger_condition,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "confidence_level": self.confidence_level
        }


class AnalysisResult(Base):
    """Stores aggregated analysis results per file."""
    __tablename__ = 'analysis_results'
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.file_id'), nullable=False)
    total_tables = Column(Integer, default=0)
    total_issues = Column(Integer, default=0)
    high_severity_count = Column(Integer, default=0)
    medium_severity_count = Column(Integer, default=0)
    low_severity_count = Column(Integer, default=0)
    risk_level = Column(String(20), nullable=True)
    risk_score = Column(Float, default=0.0)
    quality_issues_json = Column(JSON, nullable=True)
    operational_issues_json = Column(JSON, nullable=True)
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    file = relationship("UploadedFile", back_populates="analysis_results")
    
    def to_dict(self):
        return {
            "result_id": self.result_id,
            "file_id": self.file_id,
            "total_tables": self.total_tables,
            "total_issues": self.total_issues,
            "high_severity_count": self.high_severity_count,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "analysis_timestamp": self.analysis_timestamp.isoformat() if self.analysis_timestamp else None
        }


class GeminiInsight(Base):
    """Stores AI-generated insights for audit trail."""
    __tablename__ = 'gemini_insights'
    
    insight_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.file_id'), nullable=True)
    prompt_type = Column(String(50), nullable=False)  # summary, explanation, pattern
    input_json = Column(JSON, nullable=False)  # What was sent to Gemini
    output_text = Column(Text, nullable=False)  # Gemini response
    generation_timestamp = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "insight_id": self.insight_id,
            "file_id": self.file_id,
            "prompt_type": self.prompt_type,
            "output_text": self.output_text,
            "generation_timestamp": self.generation_timestamp.isoformat() if self.generation_timestamp else None
        }


class ExtractionAudit(Base):
    """Stores extraction audit for sheet completeness validation."""
    __tablename__ = 'extraction_audits'
    
    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.file_id'), nullable=False)
    total_sheets = Column(Integer, default=0)
    processed_sheets = Column(Integer, default=0)
    sheets_with_tables = Column(Integer, default=0)
    sheets_without_tables = Column(JSON, nullable=True)  # List of sheet names with no tables
    total_tables = Column(Integer, default=0)
    warnings = Column(JSON, nullable=True)  # List of warning messages
    sheet_details = Column(JSON, nullable=True)  # {sheet_name: {tables: N, rows: N}}
    audit_timestamp = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "audit_id": self.audit_id,
            "file_id": self.file_id,
            "total_sheets": self.total_sheets,
            "processed_sheets": self.processed_sheets,
            "sheets_with_tables": self.sheets_with_tables,
            "sheets_without_tables": self.sheets_without_tables,
            "total_tables": self.total_tables,
            "warnings": self.warnings,
            "sheet_details": self.sheet_details,
            "is_complete": self.total_sheets == self.processed_sheets,
            "audit_timestamp": self.audit_timestamp.isoformat() if self.audit_timestamp else None
        }


class AlertStatus(enum.Enum):
    """Alert status enum."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Alert(Base):
    """Stores proactive alerts triggered by rule thresholds."""
    __tablename__ = 'alerts'
    
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(Integer, ForeignKey('studies.study_id'), nullable=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.file_id'), nullable=True)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # high_risk, threshold_breach, trend_alert
    severity = Column(String(20), nullable=False)  # critical, warning, info
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Trigger info
    rule_id = Column(String(50), nullable=True)
    threshold_value = Column(String(50), nullable=True)
    actual_value = Column(String(50), nullable=True)
    
    # Status tracking
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    
    # Target audience
    target_role = Column(String(20), nullable=True)  # CTT, CRA, Site, or null for all
    
    def to_dict(self):
        return {
            "alert_id": self.alert_id,
            "study_id": self.study_id,
            "file_id": self.file_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "rule_id": self.rule_id,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "target_role": self.target_role
        }


class RiskTrendSnapshot(Base):
    """Stores historical risk score snapshots for trend analysis."""
    __tablename__ = 'risk_trend_snapshots'
    
    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    study_id = Column(Integer, ForeignKey('studies.study_id'), nullable=False)
    
    # Snapshot data
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    total_issues = Column(Integer, default=0)
    unique_issues = Column(Integer, default=0)
    total_files = Column(Integer, default=0)
    
    # Trend info
    previous_score = Column(Float, nullable=True)
    score_delta = Column(Float, nullable=True)  # Positive = improved, Negative = worse
    
    # Timestamp
    snapshot_time = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "snapshot_id": self.snapshot_id,
            "study_id": self.study_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "total_issues": self.total_issues,
            "unique_issues": self.unique_issues,
            "total_files": self.total_files,
            "previous_score": self.previous_score,
            "score_delta": self.score_delta,
            "snapshot_time": self.snapshot_time.isoformat() if self.snapshot_time else None,
            "trend": "improving" if self.score_delta and self.score_delta < 0 else "worsening" if self.score_delta and self.score_delta > 0 else "stable"
        }


def get_engine(db_path: str = "database/clinical_trials.db"):
    """Create database engine."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_database(db_path: str = "database/clinical_trials.db"):
    """Initialize database and create all tables if they don't exist."""
    engine = get_engine(db_path)
    # checkfirst=True prevents errors if tables already exist
    Base.metadata.create_all(engine, checkfirst=True)
    return engine


def get_session(engine):
    """Create a new session."""
    Session = sessionmaker(bind=engine)
    return Session()
