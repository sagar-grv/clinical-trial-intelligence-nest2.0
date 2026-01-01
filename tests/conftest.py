"""
Pytest fixtures and configuration for Clinical Trial Intelligence tests.
"""
import pytest
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Base, get_engine, init_database, Study, UploadedFile
from database.storage import DatabaseStorage


@pytest.fixture(scope="function")
def temp_db_path():
    """Create a temporary database file for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup after test - ignore if file is locked (Windows)
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass  # Windows file lock, will be cleaned up later


@pytest.fixture(scope="function")
def db_engine(temp_db_path):
    """Create a fresh database engine for each test."""
    engine = init_database(temp_db_path)
    return engine


@pytest.fixture(scope="function")
def db_storage(temp_db_path):
    """Create a DatabaseStorage instance with a fresh database."""
    init_database(temp_db_path)
    storage = DatabaseStorage(temp_db_path)
    return storage


@pytest.fixture
def sample_excel_bytes():
    """Create a sample Excel file in memory for testing."""
    import pandas as pd
    import io
    
    # Create sample data
    df = pd.DataFrame({
        "Site ID": ["Site 1", "Site 2", "Site 3"],
        "Subject ID": ["S001", "S002", "S003"],
        "Visit": ["Visit 1", "Visit 2", "Visit 3"],
        "Status": ["Complete", "Pending", "Missing"]
    })
    
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name="TestData")
    buffer.seek(0)
    return buffer


@pytest.fixture
def sample_empty_excel_bytes():
    """Create an empty Excel file for testing edge cases."""
    import pandas as pd
    import io
    
    df = pd.DataFrame()
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Empty")
    buffer.seek(0)
    return buffer


@pytest.fixture
def sample_multi_sheet_excel_bytes():
    """Create a multi-sheet Excel file for testing."""
    import pandas as pd
    import io
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Sheet 1: Clinical data
        df1 = pd.DataFrame({
            "Subject ID": ["S001", "S002"],
            "Age": [45, 52],
            "Status": ["Active", "Complete"]
        })
        df1.to_excel(writer, sheet_name="Clinical", index=False)
        
        # Sheet 2: Safety data
        df2 = pd.DataFrame({
            "Subject ID": ["S001"],
            "AE Type": ["Headache"],
            "Severity": ["Mild"]
        })
        df2.to_excel(writer, sheet_name="Safety", index=False)
        
        # Sheet 3: Empty (metadata only)
        df3 = pd.DataFrame(columns=["Col1", "Col2"])
        df3.to_excel(writer, sheet_name="Metadata", index=False)
    
    buffer.seek(0)
    return buffer
