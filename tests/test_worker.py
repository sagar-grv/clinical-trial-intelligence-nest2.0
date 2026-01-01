"""
Tests for AnalysisWorker - background processing logic.
"""
import pytest
import time
import threading

from core.worker import AnalysisWorker, start_async_analysis
from database.models import init_database, AnalysisStatus
from database.storage import DatabaseStorage


class TestAnalysisWorkerBasics:
    """Test basic worker functionality."""
    
    @pytest.fixture
    def db_storage(self, temp_db_path):
        init_database(temp_db_path)
        return DatabaseStorage(temp_db_path)
    
    def test_worker_initialization(self, db_storage):
        """Test that worker initializes correctly."""
        study = db_storage.get_or_create_study("Worker Test Study")
        
        worker = AnalysisWorker(study.study_id, db_storage.db_path)
        
        assert worker.study_id == study.study_id
        assert worker.db_path == db_storage.db_path
        assert isinstance(worker, threading.Thread)
    
    def test_worker_is_daemon(self, db_storage):
        """Test that worker runs as daemon thread."""
        study = db_storage.get_or_create_study("Daemon Test Study")
        
        worker = AnalysisWorker(study.study_id, db_storage.db_path)
        
        assert worker.daemon is True


class TestStatusUpdates:
    """Test worker status update mechanism."""
    
    @pytest.fixture
    def db_storage(self, temp_db_path):
        init_database(temp_db_path)
        return DatabaseStorage(temp_db_path)
    
    def test_initial_status_pending(self, db_storage):
        """Test that new studies start with PENDING status."""
        study = db_storage.get_or_create_study("Initial Status Test")
        
        assert study.analysis_status == AnalysisStatus.PENDING.value
    
    def test_status_transitions(self, db_storage):
        """Test that status can be updated through the workflow."""
        study = db_storage.get_or_create_study("Transition Test")
        
        # Simulate workflow: PENDING -> RUNNING -> COMPLETED
        db_storage.update_study_status(
            study.study_id, 
            AnalysisStatus.RUNNING.value, 
            progress=0
        )
        
        updated = db_storage.get_study_by_id(study.study_id)
        assert updated.analysis_status == AnalysisStatus.RUNNING.value
        
        db_storage.update_study_status(
            study.study_id, 
            AnalysisStatus.COMPLETED.value, 
            progress=100
        )
        
        completed = db_storage.get_study_by_id(study.study_id)
        assert completed.analysis_status == AnalysisStatus.COMPLETED.value
        assert completed.analysis_progress == 100


class TestAsyncAnalysisStart:
    """Test the start_async_analysis helper."""
    
    @pytest.fixture
    def db_storage(self, temp_db_path):
        init_database(temp_db_path)
        return DatabaseStorage(temp_db_path)
    
    def test_start_async_returns_worker(self, db_storage):
        """Test that start_async_analysis returns a worker object."""
        study = db_storage.get_or_create_study("Async Start Test")
        
        worker = start_async_analysis(study.study_id, db_storage.db_path)
        
        assert worker is not None
        assert isinstance(worker, AnalysisWorker)
        
        # Clean up - wait briefly then move on
        # Worker will complete or timeout on its own
