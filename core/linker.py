"""
Cross-File Linker - Links data across files using common identifiers
"""
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd
from .standardizer import IdentifierStandardizer


class CrossFileLinker:
    """Links data across multiple files using common identifiers."""
    
    def __init__(self):
        self.standardizer = IdentifierStandardizer()
        self.link_map: Dict[str, Dict] = {}  # study_id -> linking info
    
    def analyze_linkability(self, study_id: str, file_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Analyze how files in a study can be linked.
        Returns linking metadata without physically merging files.
        """
        linkability = {
            "study_id": study_id,
            "files": [],
            "common_identifiers": [],
            "link_paths": []
        }
        
        # Analyze each file
        file_identifiers = {}
        for file_name, df in file_data.items():
            if df is None or df.empty:
                continue
                
            identifiers = self.standardizer.find_identifier_columns(df)
            file_identifiers[file_name] = set(identifiers.keys())
            
            linkability["files"].append({
                "name": file_name,
                "identifiers": list(identifiers.keys()),
                "row_count": len(df)
            })
        
        # Find common identifiers across all files
        if file_identifiers:
            common = set.intersection(*file_identifiers.values()) if file_identifiers else set()
            linkability["common_identifiers"] = list(common)
        
        # Determine link paths
        for id_type in ["site_id", "subject_id", "visit"]:
            files_with_id = [f for f, ids in file_identifiers.items() if id_type in ids]
            if len(files_with_id) > 1:
                linkability["link_paths"].append({
                    "identifier": id_type,
                    "linkable_files": files_with_id
                })
        
        self.link_map[study_id] = linkability
        return linkability
    
    def get_linked_values(self, study_id: str, identifier: str, 
                          file_data: Dict[str, pd.DataFrame]) -> Dict[str, List]:
        """
        Get unique values for an identifier across all files in a study.
        Enables cross-file analysis without physical merging.
        """
        values_by_file = {}
        
        for file_name, df in file_data.items():
            if df is None or df.empty:
                continue
            
            id_cols = self.standardizer.find_identifier_columns(df)
            if identifier in id_cols:
                original_col = id_cols[identifier]
                values = df[original_col].dropna().unique().tolist()
                values_by_file[file_name] = values
        
        return values_by_file
    
    def get_sites_across_files(self, study_id: str, file_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Get all unique site IDs across all files in a study."""
        all_sites = set()
        
        for file_name, df in file_data.items():
            if df is None or df.empty:
                continue
            
            sites = self.standardizer.extract_identifier_values(df, "site_id")
            all_sites.update([str(s) for s in sites])
        
        return sorted(list(all_sites))
    
    def create_site_file_matrix(self, study_id: str, 
                                 file_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Create a matrix showing which sites appear in which files.
        Useful for understanding data coverage.
        """
        all_sites = self.get_sites_across_files(study_id, file_data)
        matrix_data = {"Site": all_sites}
        
        for file_name, df in file_data.items():
            if df is None or df.empty:
                matrix_data[file_name] = [False] * len(all_sites)
                continue
            
            sites_in_file = set(str(s) for s in 
                              self.standardizer.extract_identifier_values(df, "site_id"))
            matrix_data[file_name] = [site in sites_in_file for site in all_sites]
        
        return pd.DataFrame(matrix_data)
