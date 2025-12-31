"""
Background Worker - Handles asynchronous study analysis
"""
import threading
import time
import traceback
from typing import Dict
from database.models import AnalysisStatus
from core.pipeline import ProcessingPipeline

class AnalysisWorker(threading.Thread):
    """
    Background thread for running heavy study analysis.
    Updates DB status during execution.
    """
    
    def __init__(self, study_id: int, db_path: str = "database/clinical_trials.db"):
        super().__init__()
        self.study_id = study_id
        self.db_path = db_path
        self.daemon = True  # Daemon thread so it doesn't block exit
        
    def run(self):
        """Execute the analysis pipeline."""
        pipeline = None
        try:
            # Create fresh pipeline for this thread (thread-safe DB session)
            pipeline = ProcessingPipeline(self.db_path)
            storage = pipeline.storage
            
            # 1. Update status to RUNNING
            storage.update_study_status(self.study_id, AnalysisStatus.RUNNING.value, 10)
            print(f"[Worker] Started analysis for Study {self.study_id}")
            
            # 2. Run Analytics (Heavy computation)
            # This calculates issues, risk, and deduplicates
            result = pipeline.analyze_study(self.study_id)
            
            if not result.get("success"):
                error_msg = "; ".join(result.get("errors", []))
                raise Exception(f"Analysis pipeline failed: {error_msg}")
            
            # Update progress
            storage.update_study_status(self.study_id, AnalysisStatus.RUNNING.value, 50)
            
            # 3. Generate AI Insights (Network call, slow)
            pipeline.generate_study_insights(self.study_id)
            
            # Update progress
            storage.update_study_status(self.study_id, AnalysisStatus.RUNNING.value, 80)
            
            # 4. Prepare Cache
            # Fetch the complete data structure that the UI needs
            full_data = pipeline.get_study_full_analysis(self.study_id)
            
            # 5. Save Cache & Complete
            storage.update_study_analytics(
                 study_id=self.study_id,
                 total_issues=result["total_issues"],
                 unique_issues=result["unique_issues"],
                 risk_level=result["risk_level"],
                 risk_score=result["risk_score"],
                 cached_analytics=full_data  # Save the JSON blob for lazy loading
            )
            
            storage.update_study_status(self.study_id, AnalysisStatus.COMPLETED.value, 100)
            print(f"[Worker] Completed analysis for Study {self.study_id}")
            
        except Exception as e:
            print(f"[Worker] Failed analysis for Study {self.study_id}: {e}")
            traceback.print_exc()
            if pipeline:
                pipeline.storage.update_study_status(self.study_id, AnalysisStatus.FAILED.value, 0)


def start_async_analysis(study_id: int, db_path: str = "database/clinical_trials.db"):
    """Helper to start the worker."""
    worker = AnalysisWorker(study_id, db_path)
    worker.start()
    return worker
