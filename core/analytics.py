"""
Analytics Engine - Aggregates insights across the system
"""
from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path

from .ingestion import FileIngestionEngine
from .classifier import FileClassifier
from .registry import MetadataRegistry
from .quality_detector import DataQualityDetector
from .operational_detector import OperationalDetector
from .risk_scorer import RiskScorer


class AnalyticsEngine:
    """Main analytics engine that orchestrates all analysis components."""
    
    def __init__(self, data_lake_path: Path):
        self.data_lake_path = data_lake_path
        self.ingestion = FileIngestionEngine(data_lake_path)
        self.classifier = FileClassifier()
        self.registry = MetadataRegistry()
        self.quality_detector = DataQualityDetector()
        self.operational_detector = OperationalDetector()
        self.risk_scorer = RiskScorer()
        
        self._initialized = False
        self._study_cache: Dict[str, Dict] = {}
    
    def initialize(self) -> Dict:
        """Initialize the system by ingesting and classifying all files."""
        files = self.ingestion.ingest_all_studies()
        files = self.classifier.classify_files(files)
        self.registry.register(files)
        self._initialized = True
        return self.registry.get_summary()
    
    def get_studies(self) -> List[str]:
        """Get list of all study IDs."""
        if not self._initialized:
            self.initialize()
        return self.registry.get_all_studies()
    
    def analyze_study(self, study_id: str, force_refresh: bool = False) -> Dict:
        """Complete analysis of a single study."""
        if not self._initialized:
            self.initialize()
        
        if study_id in self._study_cache and not force_refresh:
            return self._study_cache[study_id]
        
        study_files = self.registry.get_files_by_study(study_id)
        if not study_files:
            return {"error": f"Study {study_id} not found"}
        
        # Load file data
        file_data = {}
        for f in study_files:
            df = self.ingestion.load_file_data(f["file_path"])
            if df is not None:
                file_data[f["file_name"]] = (df, f["category"])
        
        # Detect issues
        quality_results = self.quality_detector.analyze_study(study_id, file_data)
        operational_results = self.operational_detector.analyze_study(study_id, file_data)
        
        # Calculate risks
        site_risks = self.risk_scorer.score_all_sites(
            quality_results.get("by_site", {}),
            operational_results.get("by_site", {})
        )
        study_risk = self.risk_scorer.calculate_study_risk(site_risks)
        
        result = {
            "study_id": study_id,
            "file_count": len(study_files),
            "files": study_files,
            "quality_issues": quality_results,
            "operational_issues": operational_results,
            "site_risks": site_risks,
            "study_risk": study_risk,
            "categories": self.registry.get_study_categories(study_id)
        }
        
        self._study_cache[study_id] = result
        return result
    
    def get_all_studies_summary(self) -> List[Dict]:
        """Get summary for all studies."""
        summaries = []
        for study_id in self.get_studies():
            analysis = self.analyze_study(study_id)
            summaries.append({
                "study_id": study_id,
                "file_count": analysis.get("file_count", 0),
                "risk_level": analysis.get("study_risk", {}).get("risk_level", "Unknown"),
                "high_risk_sites": analysis.get("study_risk", {}).get("high_risk_sites", 0),
                "total_sites": analysis.get("study_risk", {}).get("total_sites", 0),
                "quality_issues": analysis.get("quality_issues", {}).get("total_issues", 0),
                "operational_issues": analysis.get("operational_issues", {}).get("total_issues", 0)
            })
        return summaries
