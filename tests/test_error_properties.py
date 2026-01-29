import pytest
from hypothesis import given, strategies as st
import tempfile
from pathlib import Path
from document_processor_gui.core.error_handler import ErrorHandler
from document_processor_gui.core.exceptions import (
    DocumentProcessorError, ValidationError, FileSystemError
)

@given(st.text())
def test_error_handling_robustness(msg):
    """
    Property 11: Error Handling and Recovery
    Validates: Requirements 11.1, 11.2, 11.3
    
    Any error should be handled gracefully returning a message string.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        handler = ErrorHandler(log_dir=Path(temp_dir))
        
        # Test with standard exception
        error_msg = handler.handle_error(Exception(msg))
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0
        
        # Test with custom exception
        custom_error = DocumentProcessorError(msg)
        error_msg = handler.handle_error(custom_error)
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0
        
        # Verify log file exists and is not empty
        log_files = list(Path(temp_dir).glob("*.log"))
        assert len(log_files) == 1
        assert log_files[0].stat().st_size > 0
