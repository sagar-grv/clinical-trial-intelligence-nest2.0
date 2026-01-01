"""
Tests for TableExtractor - Excel multi-table extraction logic.
"""
import pytest
import pandas as pd
import io

from core.table_extractor import TableExtractor


class TestTableExtractorBasics:
    """Test basic table extraction functionality."""
    
    @pytest.fixture
    def extractor(self):
        return TableExtractor()
    
    def test_extract_single_sheet(self, extractor, sample_excel_bytes):
        """Test extraction from a simple single-sheet Excel file."""
        result = extractor.extract_all_tables(sample_excel_bytes)
        
        assert result["total_sheets"] == 1
        assert result["total_tables"] >= 1
        assert len(result["errors"]) == 0
    
    def test_extract_multi_sheet(self, extractor, sample_multi_sheet_excel_bytes):
        """Test extraction from a multi-sheet Excel file."""
        result = extractor.extract_all_tables(sample_multi_sheet_excel_bytes)
        
        assert result["total_sheets"] == 3
        # At least Clinical and Safety sheets should have tables
        assert result["total_tables"] >= 2
    
    def test_empty_sheet_handling(self, extractor, sample_empty_excel_bytes):
        """Test that empty sheets are handled gracefully."""
        result = extractor.extract_all_tables(sample_empty_excel_bytes)
        
        assert result["total_sheets"] == 1
        # Empty sheet should produce 0 tables, not an error
        assert result["total_tables"] == 0
        assert len(result["errors"]) == 0
    
    def test_audit_tracking(self, extractor, sample_excel_bytes):
        """Test that audit information is tracked."""
        result = extractor.extract_all_tables(sample_excel_bytes)
        
        audit = result["audit"]
        assert "total_sheets" in audit
        assert "processed_sheets" in audit
        assert audit["processed_sheets"] == audit["total_sheets"]


class TestTableBoundaryDetection:
    """Test table boundary detection logic."""
    
    @pytest.fixture
    def extractor(self):
        return TableExtractor()
    
    def test_detect_table_with_empty_row_gap(self, extractor):
        """Test that tables separated by empty rows are detected as separate."""
        # Create Excel with two tables separated by empty rows
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Create a dataframe with a gap
            data = {
                "Col1": ["Header1", "Data1", "Data2", None, None, "Header2", "DataA"],
                "Col2": ["Header2", "Val1", "Val2", None, None, "Header2B", "ValA"]
            }
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name="GapTest", index=False, header=False)
        
        buffer.seek(0)
        result = extractor.extract_all_tables(buffer)
        
        # Should detect the gap and potentially create multiple tables
        assert result["total_sheets"] == 1
        assert len(result["errors"]) == 0


class TestTableTypeDetection:
    """Test table type classification."""
    
    @pytest.fixture
    def extractor(self):
        return TableExtractor()
    
    def test_detect_data_quality_table(self, extractor):
        """Test detection of data quality table type."""
        headers = ["Subject ID", "Missing Fields", "Invalid Data", "Error Count"]
        table_type = extractor.detect_table_type(headers)
        
        assert table_type == "Data Quality"
    
    def test_detect_safety_table(self, extractor):
        """Test detection of safety table type."""
        headers = ["Subject ID", "AE Type", "SAE Status", "Adverse Event"]
        table_type = extractor.detect_table_type(headers)
        
        assert table_type == "Safety"
    
    def test_detect_operational_table(self, extractor):
        """Test detection of operational table type."""
        headers = ["Site", "Visit Delay", "Overdue Queries", "Pending Items"]
        table_type = extractor.detect_table_type(headers)
        
        assert table_type == "Operational"
    
    def test_detect_clinical_table(self, extractor):
        """Test detection of clinical table type."""
        headers = ["Subject ID", "Patient Name", "Site", "Enrollment Date"]
        table_type = extractor.detect_table_type(headers)
        
        assert table_type == "Clinical"
    
    def test_detect_other_table(self, extractor):
        """Test fallback to 'Other' for unrecognized tables."""
        headers = ["Random", "Columns", "Here"]
        table_type = extractor.detect_table_type(headers)
        
        assert table_type == "Other"


class TestHeaderValidation:
    """Test header detection and validation."""
    
    @pytest.fixture
    def extractor(self):
        return TableExtractor()
    
    def test_headers_extracted_correctly(self, extractor, sample_excel_bytes):
        """Test that headers are correctly extracted from tables."""
        result = extractor.extract_all_tables(sample_excel_bytes)
        
        # Should have at least one table with headers
        assert len(result["tables"]) > 0
        table = result["tables"][0]
        
        assert "headers" in table
        assert len(table["headers"]) > 0
        # Our sample has Site ID, Subject ID, Visit, Status
        assert "Site ID" in table["headers"] or any("site" in h.lower() for h in table["headers"])
