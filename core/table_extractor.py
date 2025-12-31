"""
Multi-Table Extractor - Extracts ALL tables from ALL sheets in Excel files
"""
from typing import List, Dict, Tuple, Optional
import pandas as pd
import io
import re


class TableExtractor:
    """
    Extracts multiple tables from Excel files.
    
    Detection methods:
    - 2+ empty row gaps indicate table boundaries
    - Repeated headers indicate new tables
    - Header pattern detection (bold, specific keywords)
    """
    
    MIN_EMPTY_ROWS_FOR_BREAK = 2
    MIN_TABLE_ROWS = 2
    
    def __init__(self):
        self.header_keywords = [
            'id', 'name', 'date', 'site', 'subject', 'visit', 'status',
            'count', 'value', 'type', 'category', 'code', 'number'
        ]
    
    def extract_all_tables(self, file_blob: io.BytesIO) -> Dict:
        """
        Extract all tables from ALL sheets in an Excel file.
        MANDATORY: Process every sheet, never skip.
        
        Returns:
            {
                "sheets": [...sheet names...],
                "tables": [...],
                "total_tables": int,
                "total_sheets": int,
                "audit": {
                    "total_sheets": int,
                    "processed_sheets": int,
                    "sheets_with_tables": int,
                    "sheets_without_tables": [...],
                    "warnings": [...],
                    "sheet_details": {sheet_name: {"tables": N, "rows": N}}
                }
            }
        """
        result = {
            "sheets": [],
            "tables": [],
            "total_tables": 0,
            "total_sheets": 0,
            "errors": [],
            "audit": {
                "total_sheets": 0,
                "processed_sheets": 0,
                "sheets_with_tables": 0,
                "sheets_without_tables": [],
                "warnings": [],
                "sheet_details": {}
            }
        }
        
        try:
            # Read Excel file
            xl = pd.ExcelFile(file_blob)
            result["sheets"] = xl.sheet_names
            result["total_sheets"] = len(xl.sheet_names)
            result["audit"]["total_sheets"] = len(xl.sheet_names)
            
            # Process EVERY sheet (no skipping)
            for sheet_name in xl.sheet_names:
                try:
                    sheet_tables = self._extract_tables_from_sheet(xl, sheet_name)
                    result["tables"].extend(sheet_tables)
                    result["audit"]["processed_sheets"] += 1
                    
                    # Track sheet details
                    total_rows = sum(t["row_count"] for t in sheet_tables)
                    result["audit"]["sheet_details"][sheet_name] = {
                        "tables": len(sheet_tables),
                        "rows": total_rows,
                        "source_type": self._detect_source_type(sheet_name)
                    }
                    
                    if sheet_tables:
                        result["audit"]["sheets_with_tables"] += 1
                        # Add is_valid indicator
                        result["audit"]["sheet_details"][sheet_name]["is_valid"] = True
                    else:
                        result["audit"]["sheets_without_tables"].append(sheet_name)
                        result["audit"]["sheet_details"][sheet_name]["is_valid"] = False
                        result["audit"]["warnings"].append(
                            f"⚠️ Sheet '{sheet_name}' has headers but no data rows (metadata-only)"
                        )
                        
                except Exception as e:
                    result["errors"].append({
                        "sheet": sheet_name,
                        "error": str(e)
                    })
                    result["audit"]["warnings"].append(
                        f"Error processing sheet '{sheet_name}': {str(e)}"
                    )
            
            result["total_tables"] = len(result["tables"])
            result["audit"]["total_tables"] = len(result["tables"])
            
            # Completeness check
            if result["audit"]["processed_sheets"] < result["audit"]["total_sheets"]:
                result["audit"]["warnings"].append(
                    f"INCOMPLETE: Only {result['audit']['processed_sheets']}/{result['audit']['total_sheets']} sheets processed"
                )
            
        except Exception as e:
            result["errors"].append({"error": f"Failed to read Excel file: {str(e)}"})
            result["audit"]["warnings"].append(f"File read error: {str(e)}")
        
        return result
    
    def _detect_source_type(self, sheet_name: str) -> str:
        """
        Detect source type for weighting.
        Cumulative = Primary (1.0), Site/CRA = Secondary (0.5)
        """
        name_lower = sheet_name.lower()
        
        if any(kw in name_lower for kw in ['cumulative', 'summary', 'aggregate', 'total']):
            return "primary"
        elif any(kw in name_lower for kw in ['site', 'cra', 'monitor', 'detail']):
            return "secondary"
        else:
            return "primary"  # Default to primary

    
    def _extract_tables_from_sheet(self, xl: pd.ExcelFile, sheet_name: str) -> List[Dict]:
        """
        Extract all tables from a single sheet with HARD ISOLATION.
        
        CRITICAL RULES:
        1. Complete state reset at start
        2. Never reuse headers/rows from other sheets
        3. Create table ONLY if header + data rows exist
        4. Strict sheet->table binding
        """
        # ============================================
        # HARD SHEET ISOLATION - Complete State Reset
        # ============================================
        tables = []           # Fresh list for this sheet only
        headers = None        # Reset headers
        row_buffer = []       # Reset row buffer
        active_table = None   # Reset active table
        
        # Read THIS sheet only - fresh DataFrame, no shared state
        try:
            df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None)
        except Exception as e:
            # Sheet read error - return empty, don't propagate state
            return []
        
        # Check for completely empty sheet
        if df_raw.empty:
            return []
        
        # Check if sheet has ONLY headers (metadata-only)
        non_empty_rows = df_raw.dropna(how='all')
        if len(non_empty_rows) <= 1:
            # Sheet has 0-1 rows - metadata-only, no table
            return []
        
        # Find table boundaries using isolated logic
        table_ranges = self._find_table_boundaries(df_raw)
        
        # Extract each table with strict validation
        for idx, (start_row, end_row) in enumerate(table_ranges):
            # CRITICAL: Create fresh extraction for this table
            table = self._extract_single_table_isolated(
                df_raw, start_row, end_row, sheet_name, idx
            )
            
            # EMPTY-TABLE GUARD: Only add if valid
            if table is not None and table.get("row_count", 0) > 0:
                tables.append(table)
        
        return tables
    
    def _extract_single_table_isolated(self, df: pd.DataFrame, start_row: int, end_row: int,
                                        sheet_name: str, table_index: int) -> Optional[Dict]:
        """
        Extract a single table with STRICT VALIDATION.
        
        Returns None if:
        - No headers
        - No data rows (headers only)
        - Cross-sheet contamination detected
        """
        # Bounds check
        if start_row >= len(df) or end_row >= len(df):
            return None
        
        # Extract slice for this table only
        table_df = df.iloc[start_row:end_row + 1].copy()  # .copy() prevents shared memory
        table_df = table_df.reset_index(drop=True)
        
        if table_df.empty:
            return None
        
        # ============================================
        # HEADER VALIDATION
        # ============================================
        first_row = table_df.iloc[0]
        headers = first_row.astype(str).tolist()
        headers = [h if h != 'nan' and h.strip() != '' else f'Column_{i}' 
                   for i, h in enumerate(headers)]
        
        # Check if headers are valid (at least one non-generic header)
        valid_headers = sum(1 for h in headers if not h.startswith('Column_'))
        if valid_headers == 0:
            return None  # No real headers
        
        # ============================================
        # DATA ROWS VALIDATION (CRITICAL)
        # ============================================
        if len(table_df) <= 1:
            # Headers only, NO data rows
            # Do NOT create table - this is metadata-only
            return None
        
        data_df = table_df.iloc[1:].copy()
        data_df.columns = headers
        
        # Convert to list of dicts
        data = data_df.to_dict(orient='records')
        
        # Clean up NaN values
        for row in data:
            for key, value in row.items():
                if pd.isna(value) or str(value) == 'nan':
                    row[key] = None
        
        # ============================================
        # EMPTY-TABLE GUARD (MANDATORY)
        # ============================================
        actual_row_count = len(data)
        
        if actual_row_count == 0:
            # CRITICAL: Do NOT create table with 0 rows
            return None
        
        # ============================================
        # STRICT SHEET->TABLE BINDING
        # ============================================
        return {
            "sheet_name": sheet_name,           # Bound to THIS sheet only
            "table_index": table_index,
            "headers": headers,
            "data": data,
            "row_count": actual_row_count,      # Actual count, not fabricated
            "column_count": len(headers),
            "start_row": start_row,
            "end_row": end_row,
            "is_valid": True                    # Data-valid indicator
        }
    
    def _find_table_boundaries(self, df: pd.DataFrame) -> List[Tuple[int, int]]:
        """
        Find table boundaries using empty row gaps and header patterns.
        
        Returns list of (start_row, end_row) tuples.
        """
        boundaries = []
        n_rows = len(df)
        
        if n_rows == 0:
            return boundaries
        
        # Track empty rows
        empty_row_mask = df.isna().all(axis=1) | (df.astype(str).apply(
            lambda row: all(cell.strip() == '' for cell in row), axis=1
        ))
        
        # Find contiguous non-empty regions
        in_table = False
        table_start = 0
        consecutive_empty = 0
        
        for i in range(n_rows):
            is_empty = empty_row_mask.iloc[i]
            
            if not is_empty:
                if not in_table:
                    # Start of new table
                    in_table = True
                    table_start = i
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                
                if in_table and consecutive_empty >= self.MIN_EMPTY_ROWS_FOR_BREAK:
                    # End of table (gap found)
                    table_end = i - consecutive_empty
                    if table_end - table_start >= self.MIN_TABLE_ROWS:
                        boundaries.append((table_start, table_end))
                    in_table = False
        
        # Handle last table
        if in_table:
            table_end = n_rows - consecutive_empty - 1
            if table_end - table_start >= self.MIN_TABLE_ROWS:
                boundaries.append((table_start, table_end))
        
        # If no boundaries found, treat entire sheet as one table
        if not boundaries and n_rows >= self.MIN_TABLE_ROWS:
            # Find first non-empty row
            first_data_row = 0
            for i in range(n_rows):
                if not empty_row_mask.iloc[i]:
                    first_data_row = i
                    break
            boundaries.append((first_data_row, n_rows - 1))
        
        # Check for repeated headers within tables (split further)
        refined_boundaries = []
        for start, end in boundaries:
            split_tables = self._split_by_repeated_headers(df, start, end)
            refined_boundaries.extend(split_tables)
        
        return refined_boundaries
    
    def _split_by_repeated_headers(self, df: pd.DataFrame, start: int, end: int) -> List[Tuple[int, int]]:
        """Split a table region if repeated headers are found."""
        if end - start < 3:  # Too small to split
            return [(start, end)]
        
        # Get first row as potential header
        first_row = df.iloc[start].astype(str).str.lower().tolist()
        header_keywords_found = sum(1 for cell in first_row if any(kw in str(cell).lower() for kw in self.header_keywords))
        
        if header_keywords_found < 2:
            return [(start, end)]  # Doesn't look like a header
        
        # Look for repeated headers
        split_points = [start]
        
        for i in range(start + 2, end):
            row = df.iloc[i].astype(str).str.lower().tolist()
            # Check if this row matches the header pattern
            matching_cells = sum(1 for j, cell in enumerate(row) if j < len(first_row) and cell == first_row[j] and cell.strip() != '')
            
            if matching_cells >= len(first_row) * 0.7 and matching_cells >= 3:  # 70% match
                split_points.append(i)
        
        split_points.append(end + 1)
        
        # Create table ranges from split points
        tables = []
        for i in range(len(split_points) - 1):
            if split_points[i + 1] - split_points[i] >= self.MIN_TABLE_ROWS:
                tables.append((split_points[i], split_points[i + 1] - 1))
        
        return tables if tables else [(start, end)]
    
    def detect_table_type(self, headers: List[str]) -> str:
        """Detect table type based on headers."""
        headers_lower = [h.lower() for h in headers]
        headers_text = ' '.join(headers_lower)
        
        # Priority order: Data Quality > Safety > Operational > Clinical
        if any(kw in headers_text for kw in ['missing', 'inactivated', 'invalid', 'error', 'blank']):
            return "Data Quality"
        if any(kw in headers_text for kw in ['sae', 'adverse', 'safety', 'ae', 'death']):
            return "Safety"
        if any(kw in headers_text for kw in ['visit', 'query', 'delay', 'overdue', 'pending']):
            return "Operational"
        if any(kw in headers_text for kw in ['subject', 'patient', 'site', 'enrollment', 'edc']):
            return "Clinical"
        
        return "Other"
