"""
Tests for database models and initialization.
"""
import pytest
import os
from sqlalchemy import inspect

from database.models import Base, get_engine, init_database, Study, UploadedFile, AnalysisStatus
from database.storage import DatabaseStorage


class TestDatabaseInitialization:
    """Test database initialization and table creation."""
    
    def test_init_database_creates_tables(self, temp_db_path):
        """Test that init_database creates all required tables."""
        engine = init_database(temp_db_path)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # Core tables should exist
        assert "studies" in table_names
        assert "uploaded_files" in table_names
        assert "detected_issues" in table_names
        assert "alerts" in table_names
        assert "risk_trend_snapshots" in table_names
    
    def test_init_database_handles_existing_tables(self, temp_db_path):
        """Test that calling init_database twice doesn't raise an error."""
        # First init
        engine1 = init_database(temp_db_path)
        
        # Second init (should not raise)
        engine2 = init_database(temp_db_path)
        
        # Both should work
        inspector = inspect(engine2)
        assert "studies" in inspector.get_table_names()
    
    def test_database_file_created(self, temp_db_path):
        """Test that the database file is actually created on disk."""
        init_database(temp_db_path)
        assert os.path.exists(temp_db_path)


class TestStudyModel:
    """Test Study model CRUD operations."""
    
    def test_create_study(self, db_storage):
        """Test creating a new study."""
        study = db_storage.get_or_create_study("Test Study Alpha")
        
        assert study is not None
        assert study.study_name == "Test Study Alpha"
        assert study.study_id is not None
    
    def test_get_study_by_id(self, db_storage):
        """Test retrieving a study by ID."""
        # Create a study first
        created = db_storage.get_or_create_study("Fetch Test Study")
        
        # Retrieve it
        fetched = db_storage.get_study_by_id(created.study_id)
        
        assert fetched is not None
        assert fetched.study_name == "Fetch Test Study"
    
    def test_get_study_by_name(self, db_storage):
        """Test retrieving a study by name."""
        db_storage.get_or_create_study("Named Study")
        
        fetched = db_storage.get_study_by_name("Named Study")
        
        assert fetched is not None
        assert fetched.study_name == "Named Study"
    
    def test_get_or_create_study_existing(self, db_storage):
        """Test that get_or_create returns existing study."""
        study1 = db_storage.get_or_create_study("Duplicate Check")
        study2 = db_storage.get_or_create_study("Duplicate Check")
        
        assert study1.study_id == study2.study_id
    
    def test_study_default_status(self, db_storage):
        """Test that new studies have PENDING analysis status."""
        study = db_storage.get_or_create_study("Status Test Study")
        
        assert study.analysis_status == AnalysisStatus.PENDING.value
    
    def test_update_study_status(self, db_storage):
        """Test updating study analysis status."""
        study = db_storage.get_or_create_study("Status Update Test")
        
        db_storage.update_study_status(
            study.study_id, 
            AnalysisStatus.RUNNING.value, 
            progress=50
        )
        
        updated = db_storage.get_study_by_id(study.study_id)
        assert updated.analysis_status == AnalysisStatus.RUNNING.value
        assert updated.analysis_progress == 50


class TestUploadedFileModel:
    """Test UploadedFile model operations."""
    
    def test_save_file(self, db_storage):
        """Test saving an uploaded file."""
        study = db_storage.get_or_create_study("File Test Study")
        
        file_record = db_storage.save_uploaded_file(
            filename="test_data.xlsx",
            file_bytes=b"fake excel content"
        )
        
        # Assign to study
        if file_record:
            db_storage.assign_file_to_study(file_record.file_id, study.study_id)
        
        assert file_record is not None
        assert file_record.file_id is not None
    
    def test_get_file(self, db_storage):
        """Test retrieving an uploaded file."""
        file_record = db_storage.save_uploaded_file(
            filename="retrieve_test.xlsx",
            file_bytes=b"content here"
        )
        
        fetched = db_storage.get_file_by_id(file_record.file_id)
        
        assert fetched is not None
        assert fetched.filename == "retrieve_test.xlsx"
    
    def test_get_study_files(self, db_storage):
        """Test getting all files for a study."""
        study = db_storage.get_or_create_study("Multi File Study")
        
        # Save and assign files
        for fname in ["file1.xlsx", "file2.xlsx", "file3.xlsx"]:
            file_record = db_storage.save_uploaded_file(fname, b"content")
            db_storage.assign_file_to_study(file_record.file_id, study.study_id)
        
        files = db_storage.get_study_files(study.study_id)
        
        assert len(files) == 3
