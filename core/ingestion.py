"""
File Ingestion Engine - Scans and registers study folders
"""
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd


class FileIngestionEngine:
    """Handles ingestion of clinical study folders and Excel files."""
    
    SUPPORTED_EXTENSIONS = ['.xlsx', '.xls']
    
    def __init__(self, data_lake_path: Path):
        self.data_lake_path = Path(data_lake_path)
        self.ingested_files: List[Dict] = []
        self.skipped_files: List[Dict] = []  # Non-Excel files
        self.empty_folders: List[str] = []
        self.malformed_files: List[Dict] = []
        
    def scan_studies(self) -> List[str]:
        """Scan and return list of study folder names."""
        if not self.data_lake_path.exists():
            return []
        
        studies = []
        for item in self.data_lake_path.iterdir():
            if item.is_dir():
                studies.append(item.name)
        return sorted(studies)
    
    def extract_study_id(self, folder_name: str) -> str:
        """Extract study ID from folder name."""
        # Pattern: "Study X_CPID_..." or "STUDY X_CPID_..."
        parts = folder_name.split('_')
        if parts:
            study_part = parts[0].strip()
            # Extract just the study number/identifier
            return study_part.replace("Study ", "").replace("STUDY ", "").strip()
        return folder_name
    
    def _scan_folder_recursive(self, folder_path: Path, study_id: str, 
                                study_folder: str) -> Tuple[List[Dict], List[Dict]]:
        """Recursively scan folder and subfolders for Excel files."""
        excel_files = []
        other_files = []
        
        for item in folder_path.iterdir():
            if item.is_dir():
                # Recursively scan subfolders
                sub_excel, sub_other = self._scan_folder_recursive(item, study_id, study_folder)
                excel_files.extend(sub_excel)
                other_files.extend(sub_other)
            elif item.is_file():
                if item.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    file_record = {
                        "study_id": study_id,
                        "study_folder": study_folder,
                        "file_name": item.name,
                        "file_path": str(item),
                        "file_size": item.stat().st_size,
                        "ingestion_timestamp": datetime.now().isoformat(),
                        "category": None,
                        "subfolder": str(item.parent.relative_to(self.data_lake_path / study_folder)) if item.parent != self.data_lake_path / study_folder else None
                    }
                    excel_files.append(file_record)
                else:
                    # Track non-Excel files
                    other_files.append({
                        "file_name": item.name,
                        "file_path": str(item),
                        "extension": item.suffix,
                        "study_id": study_id
                    })
        
        return excel_files, other_files
    
    def ingest_study(self, study_folder: str) -> List[Dict]:
        """Ingest all files from a single study folder (including subfolders)."""
        study_path = self.data_lake_path / study_folder
        if not study_path.exists():
            return []
        
        study_id = self.extract_study_id(study_folder)
        
        # Recursively scan for files
        excel_files, other_files = self._scan_folder_recursive(study_path, study_id, study_folder)
        
        # Track empty folders
        if not excel_files and not other_files:
            self.empty_folders.append(study_folder)
        
        # Track skipped non-Excel files
        self.skipped_files.extend(other_files)
        
        return excel_files
    
    def ingest_all_studies(self) -> List[Dict]:
        """Ingest all studies from the data lake."""
        all_files = []
        self.skipped_files = []
        self.empty_folders = []
        self.malformed_files = []
        
        studies = self.scan_studies()
        
        for study_folder in studies:
            files = self.ingest_study(study_folder)
            all_files.extend(files)
        
        self.ingested_files = all_files
        return all_files
    
    def load_file_data(self, file_path: str, sheet_name: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Load Excel file data into DataFrame with error handling."""
        try:
            if sheet_name:
                return pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                # Try to read first sheet
                xl = pd.ExcelFile(file_path)
                if xl.sheet_names:
                    return pd.read_excel(file_path, sheet_name=xl.sheet_names[0])
            return None
        except Exception as e:
            # Track malformed files
            self.malformed_files.append({
                "file_path": file_path,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return None
    
    def get_file_sheets(self, file_path: str) -> List[str]:
        """Get list of sheet names in an Excel file."""
        try:
            xl = pd.ExcelFile(file_path)
            return xl.sheet_names
        except Exception:
            return []
    
    def validate_file(self, file_path: str) -> Dict:
        """Validate an Excel file and return status."""
        result = {
            "file_path": file_path,
            "valid": False,
            "sheets": [],
            "error": None
        }
        
        try:
            xl = pd.ExcelFile(file_path)
            result["sheets"] = xl.sheet_names
            result["valid"] = len(xl.sheet_names) > 0
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_ingestion_summary(self) -> Dict:
        """Get summary of ingestion including skipped and malformed files."""
        return {
            "total_ingested": len(self.ingested_files),
            "total_skipped": len(self.skipped_files),
            "empty_folders": len(self.empty_folders),
            "malformed_files": len(self.malformed_files),
            "skipped_extensions": list(set(f.get("extension", "") for f in self.skipped_files))
        }
