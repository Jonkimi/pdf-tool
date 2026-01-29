"""Error handling system."""

import logging
import traceback
import sys
from typing import Optional, TYPE_CHECKING
from pathlib import Path
from datetime import datetime

from .exceptions import (
    DocumentProcessorError, ProcessingError, ValidationError, 
    FileSystemError, DependencyError, ConfigurationError
)

if TYPE_CHECKING:
    from .language_manager import LanguageManager

class ErrorHandler:
    """Handles errors, logging, and user feedback."""
    
    def __init__(self, log_dir: Optional[Path] = None, language_manager: Optional["LanguageManager"] = None):
        """Initialize error handler.
        
        Args:
            log_dir: Directory for log files
            language_manager: Optional language manager for localized messages
        """
        self.language_manager = language_manager
        
        # Set up logging
        self.logger = logging.getLogger("DocumentProcessor")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates if re-initialized
        self.logger.handlers = []
        
        if not log_dir:
            home_dir = Path.home()
            log_dir = home_dir / ".document_processor_gui" / "logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler
        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
    def handle_error(self, error: Exception, context: str = "") -> str:
        """Handle an error: log it and return a user-friendly message.
        
        Args:
            error: The exception to handle
            context: Context where error occurred
            
        Returns:
            str: User-friendly error message
        """
        # Log full traceback
        self.logger.error(f"Error in {context}: {str(error)}")
        self.logger.debug(traceback.format_exc())
        
        # Determine error category and message
        if isinstance(error, DocumentProcessorError):
            return self._format_app_error(error)
        else:
            return self._format_unexpected_error(error)

    def _format_app_error(self, error: DocumentProcessorError) -> str:
        """Format application-specific errors."""
        msg_key = "dialogs.error" # Default
        details = error.message
        
        if isinstance(error, ValidationError):
            msg_key = "messages.processing_error" 
            if hasattr(error, 'field') and error.field:
                details = f"{error.message} ({error.field})"
        elif isinstance(error, FileSystemError):
            msg_key = "messages.file_not_found" # Most common, but could be others
            if "permission" in str(error).lower():
                 msg_key = "messages.permission_denied"
            elif "space" in str(error).lower():
                 msg_key = "messages.disk_space_insufficient"
            
            if hasattr(error, 'file_path') and error.file_path:
                details = f"{error.message}: {error.file_path}"
        elif isinstance(error, DependencyError):
            msg_key = "messages.dependency_missing"
            if hasattr(error, 'dependency') and error.dependency:
                details = f"{error.message}: {error.dependency}"
            
        # Translate if possible
        if self.language_manager:
            prefix = self.language_manager.get_text(msg_key)
            # If the key returned itself, it means translation missing or just use details
            if prefix == msg_key:
                return f"Error: {details}"
            return f"{prefix}: {details}"
        
        return f"Error: {details}"

    def _format_unexpected_error(self, error: Exception) -> str:
        """Format unexpected errors."""
        msg = f"Unexpected error: {str(error)}"
        if self.language_manager:
             prefix = self.language_manager.get_text("dialogs.error")
             if prefix != "dialogs.error":
                 return f"{prefix}: {str(error)}"
        return msg

    def log_info(self, message: str):
        self.logger.info(message)
        
    def log_warning(self, message: str):
        self.logger.warning(message)
