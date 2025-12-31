"""
Core package initialization
"""
from .ingestion import FileIngestionEngine
from .classifier import FileClassifier
from .registry import MetadataRegistry
from .standardizer import IdentifierStandardizer
from .linker import CrossFileLinker
from .quality_detector import DataQualityDetector
from .operational_detector import OperationalDetector
from .risk_scorer import RiskScorer
from .analytics import AnalyticsEngine
from .table_extractor import TableExtractor
from .pipeline import ProcessingPipeline

__all__ = [
    'FileIngestionEngine',
    'FileClassifier', 
    'MetadataRegistry',
    'IdentifierStandardizer',
    'CrossFileLinker',
    'DataQualityDetector',
    'OperationalDetector',
    'RiskScorer',
    'AnalyticsEngine',
    'TableExtractor',
    'ProcessingPipeline'
]
