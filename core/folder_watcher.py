"""
Folder Watcher - Monitors data lake for new files with human-in-loop approval

Features:
- Auto-detects new Excel files in Clinical_Trial_Data_Lake folder
- Tracks processed files to avoid re-processing  
- Supports resume on connection loss
- Human approval required before processing
"""
import os
import json
from pathlib import Path
from typing import List, Tuple, Set, Dict, Optional
from datetime import datetime


class FolderWatcher:
    """
    Watches the data lake folder for new files.
    
    Human-in-Loop Design:
    - scan_for_new_files() detects files but doesn't process
    - User approves via UI
    - process_file() only runs after approval
    """
    
    STATE_FILE = "ingestion_state.json"
    
    def __init__(self, watch_path: str, storage=None, pipeline=None):
        self.watch_path = Path(watch_path)
        self.storage = storage
        self.pipeline = pipeline
        self.state_file = self.watch_path / self.STATE_FILE
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load processing state from disk for resume capability."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "processed_files": [],
            "skipped_files": [],
            "in_progress": {},
            "last_scan": None
        }
    
    def _save_state(self):
        """Persist state to disk."""
        try:
            self.state["last_scan"] = datetime.utcnow().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def scan_for_new_files(self) -> List[Tuple[str, Path]]:
        """
        Scan data lake folder for new Excel files.
        
        Returns list of (study_name, file_path) tuples awaiting approval.
        Does NOT process files - human approval required.
        """
        new_files = []
        processed = set(self.state.get("processed_files", []))
        skipped = set(self.state.get("skipped_files", []))
        
        if not self.watch_path.exists():
            return new_files
        
        for study_folder in self.watch_path.iterdir():
            if not study_folder.is_dir():
                continue
            if study_folder.name.startswith('.'):
                continue
            
            # Extract study name from folder (remove "_CPID_Input Files..." suffix)
            study_name = study_folder.name.split("_CPID_")[0].replace("_", " ").strip()
            
            for file in study_folder.glob("*.xlsx"):
                file_key = str(file.absolute())
                
                if file_key in processed or file_key in skipped:
                    continue
                
                new_files.append((study_name, file))
        
        self._save_state()
        return new_files
    
    def get_in_progress(self) -> Dict[str, Dict]:
        """Get files that were interrupted mid-processing."""
        return self.state.get("in_progress", {})
    
    def mark_in_progress(self, file_path: str, study_name: str):
        """Mark file as in-progress for resume capability."""
        self.state["in_progress"][file_path] = {
            "study_name": study_name,
            "started_at": datetime.utcnow().isoformat()
        }
        self._save_state()
    
    def mark_as_processed(self, file_path: str):
        """Mark file as successfully processed."""
        file_key = str(file_path)
        if file_key not in self.state["processed_files"]:
            self.state["processed_files"].append(file_key)
        # Remove from in-progress
        self.state["in_progress"].pop(file_key, None)
        self._save_state()
    
    def mark_as_skipped(self, file_path: str):
        """Mark file as skipped by user."""
        file_key = str(file_path)
        if file_key not in self.state["skipped_files"]:
            self.state["skipped_files"].append(file_key)
        self._save_state()
    
    def process_file(self, study_name: str, file_path: Path) -> Dict:
        """
        Process a single file after user approval.
        
        Returns processing result with success status.
        """
        if not self.storage or not self.pipeline:
            return {"success": False, "error": "Storage or pipeline not configured"}
        
        file_key = str(file_path.absolute())
        
        try:
            # Mark as in-progress for resume
            self.mark_in_progress(file_key, study_name)
            
            # Get or create study
            study = self.storage.get_or_create_study(study_name)
            
            # Read file bytes
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Save to database
            file_record = self.storage.save_uploaded_file(
                filename=file_path.name,
                file_bytes=file_bytes
            )
            
            # Assign to study
            self.storage.assign_file_to_study(file_record.file_id, study.study_id)
            
            # Process file
            result = self.pipeline.process_file(file_record.file_id)
            
            # Mark as processed on success
            if result.get("success"):
                self.mark_as_processed(file_key)
            
            return {
                "success": result.get("success", False),
                "file_id": file_record.file_id,
                "study_id": study.study_id,
                "tables_extracted": result.get("tables_extracted", 0),
                "issues_detected": result.get("issues_detected", 0)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def resume_interrupted(self) -> List[Dict]:
        """Resume any files that were interrupted mid-processing."""
        results = []
        in_progress = self.get_in_progress()
        
        for file_key, info in list(in_progress.items()):
            file_path = Path(file_key)
            if file_path.exists():
                result = self.process_file(info["study_name"], file_path)
                results.append({
                    "file": file_path.name,
                    "result": result
                })
        
        return results
    
    def clear_state(self):
        """Clear all processing state (for testing/reset)."""
        self.state = {
            "processed_files": [],
            "skipped_files": [],
            "in_progress": {},
            "last_scan": None
        }
        self._save_state()
    
    def get_statistics(self) -> Dict:
        """Get watcher statistics."""
        return {
            "processed_count": len(self.state.get("processed_files", [])),
            "skipped_count": len(self.state.get("skipped_files", [])),
            "in_progress_count": len(self.state.get("in_progress", {})),
            "last_scan": self.state.get("last_scan")
        }


# Convenience function for creating watcher
def create_watcher(watch_path: str = None):
    """Create a folder watcher with default data lake path."""
    if watch_path is None:
        from config import DATA_LAKE_PATH
        watch_path = str(DATA_LAKE_PATH)
    return FolderWatcher(watch_path)
