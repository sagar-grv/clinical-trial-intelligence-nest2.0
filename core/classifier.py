"""
File Classification Engine - Categorizes files based on keywords
"""
from typing import Dict, List, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import FILE_CLASSIFICATION, CLASSIFICATION_PRIORITY


class FileClassifier:
    """Classifies files based on filename keywords."""
    
    def __init__(self):
        self.classification_rules = FILE_CLASSIFICATION
        self.priority = CLASSIFICATION_PRIORITY
    
    def classify_file(self, file_name: str) -> str:
        """
        Classify a file based on its name.
        Priority: Data Quality > Safety > Operational > Clinical
        """
        file_name_lower = file_name.lower()
        matches = []
        
        for category, keywords in self.classification_rules.items():
            for keyword in keywords:
                if keyword in file_name_lower:
                    matches.append(category)
                    break  # One match per category is enough
        
        if not matches:
            return "Other"
        
        # Sort by priority (descending) and return highest priority match
        matches.sort(key=lambda x: self.priority.get(x, 0), reverse=True)
        return matches[0]
    
    def classify_files(self, files: List[Dict]) -> List[Dict]:
        """Classify all files and add category to their metadata."""
        for file_record in files:
            file_record["category"] = self.classify_file(file_record["file_name"])
        return files
    
    def get_category_summary(self, files: List[Dict]) -> Dict[str, int]:
        """Get count of files per category."""
        summary = {}
        for file_record in files:
            category = file_record.get("category", "Other")
            summary[category] = summary.get(category, 0) + 1
        return summary
    
    def get_files_by_category(self, files: List[Dict], category: str) -> List[Dict]:
        """Filter files by category."""
        return [f for f in files if f.get("category") == category]
