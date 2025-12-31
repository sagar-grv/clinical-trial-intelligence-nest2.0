"""
Identifier Standardizer - Normalizes column names and values across files
"""
from typing import Dict, List, Optional, Set
import pandas as pd
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import IDENTIFIER_MAPPING


class IdentifierStandardizer:
    """Standardizes identifiers across different files and sources."""
    
    def __init__(self):
        self.mapping = IDENTIFIER_MAPPING
        self._reverse_mapping = self._build_reverse_mapping()
    
    def _build_reverse_mapping(self) -> Dict[str, str]:
        """Build reverse mapping from variant names to standard names."""
        reverse = {}
        for standard, variants in self.mapping.items():
            for variant in variants:
                reverse[variant.lower()] = standard
        return reverse
    
    def standardize_column_name(self, column_name: str) -> str:
        """Convert a column name to its standard form."""
        col_lower = column_name.lower().strip()
        return self._reverse_mapping.get(col_lower, column_name)
    
    def standardize_dataframe_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize all column names in a DataFrame."""
        new_columns = {}
        for col in df.columns:
            std_name = self.standardize_column_name(str(col))
            new_columns[col] = std_name
        return df.rename(columns=new_columns)
    
    def normalize_site_id(self, value) -> str:
        """Normalize Site ID values (e.g., site1, Site 001, 001 -> 1)."""
        if pd.isna(value):
            return None
        val_str = str(value).lower().strip()
        # Remove common prefixes
        val_str = re.sub(r'^(site|site_|site-|site\s*)', '', val_str, flags=re.IGNORECASE)
        # Remove leading zeros and extract number
        match = re.search(r'(\d+)', val_str)
        if match:
            return str(int(match.group(1)))
        return val_str
    
    def normalize_subject_id(self, value) -> str:
        """Normalize Subject ID values."""
        if pd.isna(value):
            return None
        val_str = str(value).strip()
        # Remove common prefixes
        val_str = re.sub(r'^(subj|subject|patient|pt)[\s_-]*', '', val_str, flags=re.IGNORECASE)
        return val_str
    
    def normalize_visit(self, value) -> str:
        """Normalize Visit labels (e.g., Visit 1, V1, First Visit -> Visit 1)."""
        if pd.isna(value):
            return None
        val_str = str(value).lower().strip()
        
        # Map ordinal words to numbers
        ordinals = {'first': '1', 'second': '2', 'third': '3', 'fourth': '4', 
                   'fifth': '5', 'sixth': '6', 'seventh': '7', 'eighth': '8'}
        for word, num in ordinals.items():
            if word in val_str:
                return f"Visit {num}"
        
        # Extract visit number from various formats
        match = re.search(r'v(?:isit)?[\s_-]*(\d+)', val_str, re.IGNORECASE)
        if match:
            return f"Visit {match.group(1)}"
        
        # Try to find just a number
        match = re.search(r'(\d+)', val_str)
        if match:
            return f"Visit {match.group(1)}"
        
        return val_str.title()
    
    def find_identifier_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Find which standard identifiers exist in a DataFrame."""
        found = {}
        for col in df.columns:
            std_name = self.standardize_column_name(str(col))
            if std_name in self.mapping:
                found[std_name] = col
        return found
    
    def get_common_identifiers(self, dataframes: List[pd.DataFrame]) -> Set[str]:
        """Find identifiers common to all DataFrames."""
        if not dataframes:
            return set()
        
        common = None
        for df in dataframes:
            identifiers = set(self.find_identifier_columns(df).keys())
            if common is None:
                common = identifiers
            else:
                common = common.intersection(identifiers)
        
        return common or set()
    
    def extract_identifier_values(self, df: pd.DataFrame, identifier: str) -> List:
        """Extract unique values for a given identifier from DataFrame."""
        id_columns = self.find_identifier_columns(df)
        if identifier in id_columns:
            original_col = id_columns[identifier]
            values = df[original_col].dropna().unique().tolist()
            # Normalize values based on identifier type
            if identifier == "site_id":
                values = [self.normalize_site_id(v) for v in values if v is not None]
            elif identifier == "subject_id":
                values = [self.normalize_subject_id(v) for v in values if v is not None]
            elif identifier == "visit":
                values = [self.normalize_visit(v) for v in values if v is not None]
            return [v for v in values if v is not None]
        return []
