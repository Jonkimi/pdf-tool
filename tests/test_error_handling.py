import pytest
from pathlib import Path
import tempfile
from unittest.mock import Mock
from document_processor_gui.core.error_handler import ErrorHandler
from document_processor_gui.core.exceptions import (
    ValidationError, FileSystemError, DependencyError
)

class TestErrorHandler:
    
    def test_validation_error_handling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = ErrorHandler(log_dir=Path(temp_dir))
            error = ValidationError("Invalid value", field="age")
            msg = handler.handle_error(error)
            
            assert "Invalid value" in msg
            assert "age" in msg
            
    def test_filesystem_error_handling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = ErrorHandler(log_dir=Path(temp_dir))
            error = FileSystemError("File not found", file_path="/tmp/missing")
            msg = handler.handle_error(error)
            
            assert "File not found" in msg
            assert "/tmp/missing" in msg

    def test_dependency_error_handling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = ErrorHandler(log_dir=Path(temp_dir))
            error = DependencyError("Missing tool", dependency="ghostscript")
            msg = handler.handle_error(error)
            
            assert "Missing tool" in msg
            assert "ghostscript" in msg
            
    def test_with_language_manager(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_lang_manager = Mock()
            mock_lang_manager.get_text.return_value = "Translated Error"
            
            handler = ErrorHandler(log_dir=Path(temp_dir), language_manager=mock_lang_manager)
            error = ValidationError("Bad input")
            msg = handler.handle_error(error)
            
            assert "Translated Error" in msg
            # Check that get_text was called with the correct key for ValidationError
            mock_lang_manager.get_text.assert_called_with("messages.processing_error")
