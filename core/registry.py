"""
Metadata Registry - Central storage for file metadata
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path


class MetadataRegistry:
    """Central registry for all ingested file metadata."""
    
    def __init__(self):
        self.records: List[Dict] = []
        self.index_by_study: Dict[str, List[Dict]] = {}
        self.index_by_category: Dict[str, List[Dict]] = {}
        self.last_updated: Optional[str] = None
    
    def register(self, files: List[Dict]) -> None:
        """Register files in the metadata registry."""
        self.records = files
        self._build_indices()
        self.last_updated = datetime.now().isoformat()
    
    def _build_indices(self) -> None:
        """Build lookup indices for fast querying."""
        self.index_by_study = {}
        self.index_by_category = {}
        
        for record in self.records:
            # Index by study
            study_id = record.get("study_id", "Unknown")
            if study_id not in self.index_by_study:
                self.index_by_study[study_id] = []
            self.index_by_study[study_id].append(record)
            
            # Index by category
            category = record.get("category", "Other")
            if category not in self.index_by_category:
                self.index_by_category[category] = []
            self.index_by_category[category].append(record)
    
    def get_all_studies(self) -> List[str]:
        """Get list of all study IDs."""
        return sorted(self.index_by_study.keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))
    
    def get_files_by_study(self, study_id: str) -> List[Dict]:
        """Get all files for a specific study."""
        return self.index_by_study.get(study_id, [])
    
    def get_files_by_category(self, category: str) -> List[Dict]:
        """Get all files in a specific category."""
        return self.index_by_category.get(category, [])
    
    def get_study_categories(self, study_id: str) -> Dict[str, List[Dict]]:
        """Get files grouped by category for a specific study."""
        study_files = self.get_files_by_study(study_id)
        categories = {}
        for f in study_files:
            cat = f.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f)
        return categories
    
    def get_all_categories(self) -> List[str]:
        """Get list of all categories."""
        return list(self.index_by_category.keys())
    
    def get_record_count(self) -> int:
        """Get total number of registered files."""
        return len(self.records)
    
    def get_study_count(self) -> int:
        """Get total number of studies."""
        return len(self.index_by_study)
    
    def get_summary(self) -> Dict:
        """Get registry summary statistics."""
        return {
            "total_files": self.get_record_count(),
            "total_studies": self.get_study_count(),
            "categories": {cat: len(files) for cat, files in self.index_by_category.items()},
            "last_updated": self.last_updated
        }
    
    def find_file(self, study_id: str, partial_name: str) -> Optional[Dict]:
        """Find a file by study ID and partial filename match."""
        study_files = self.get_files_by_study(study_id)
        partial_lower = partial_name.lower()
        for f in study_files:
            if partial_lower in f["file_name"].lower():
                return f
        return None
    
    def search_files(self, query: str, study_id: Optional[str] = None) -> List[Dict]:
        """Search files by name across all studies or within a specific study."""
        query_lower = query.lower()
        results = []
        
        if study_id:
            files_to_search = self.get_files_by_study(study_id)
        else:
            files_to_search = self.records
        
        for f in files_to_search:
            if query_lower in f["file_name"].lower():
                results.append(f)
        
        return results
    
    def get_file_by_path(self, file_path: str) -> Optional[Dict]:
        """Find a file record by its exact path."""
        for f in self.records:
            if f.get("file_path") == file_path:
                return f
        return None
    
    def get_files_with_issues(self, study_id: str, issues: List[Dict]) -> List[Dict]:
        """Get file records that contributed to specific issues."""
        file_names = set()
        for issue in issues:
            file_name = issue.get("file")
            if file_name:
                file_names.add(file_name)
        
        study_files = self.get_files_by_study(study_id)
        return [f for f in study_files if f.get("file_name") in file_names]
    
    def check_for_duplicates(self) -> List[Dict]:
        """Find potential duplicate files across studies."""
        duplicates = []
        seen = {}
        
        for f in self.records:
            name_lower = f["file_name"].lower()
            if name_lower in seen:
                duplicates.append({
                    "file": f,
                    "duplicate_of": seen[name_lower]
                })
            else:
                seen[name_lower] = f
        
        return duplicates
