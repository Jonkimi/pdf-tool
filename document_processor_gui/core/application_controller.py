"""Application controller - central coordination between GUI and processing engines."""

import logging
import threading
from typing import Optional, Callable, Dict, Any, List, TYPE_CHECKING
from dataclasses import asdict

from ..processing.models import ProcessingResults
from ..processing.conversion_engine import ConversionEngine
from ..processing.compression_engine import CompressionEngine
from ..processing.labeling_engine import LabelingEngine
from ..backend.word_converter import WordConverter
from ..backend.ghostscript_wrapper import GhostscriptWrapper
from ..backend.pdf_labeler import PDFLabeler
from ..backend.conversion_backend import ConversionBackendType

if TYPE_CHECKING:
    from ..config import ConfigurationManager
    from .error_handler import ErrorHandler
    from .language_manager import LanguageManager


class ApplicationController:
    """Main application controller that coordinates GUI and processing engines."""

    def __init__(self, config_manager: "ConfigurationManager",
                 error_handler: Optional["ErrorHandler"] = None,
                 language_manager: Optional["LanguageManager"] = None):
        """Initialize application controller.

        Args:
            config_manager: Configuration manager instance
            error_handler: Error handler instance (optional)
            language_manager: Language manager instance (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.error_handler = error_handler
        self.language_manager = language_manager

        # Processing state
        self._current_operation: Optional[threading.Thread] = None
        self._cancel_requested = False
        self._is_processing = False

        # Initialize backend services
        self._word_converter: Optional[WordConverter] = None
        self._gs_wrapper: Optional[GhostscriptWrapper] = None
        self._pdf_labeler: Optional[PDFLabeler] = None

        # Initialize processing engines
        self._conversion_engine: Optional[ConversionEngine] = None
        self._compression_engine: Optional[CompressionEngine] = None
        self._labeling_engine: Optional[LabelingEngine] = None

        # Callbacks for GUI updates
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._completion_callback: Optional[Callable[[ProcessingResults], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None

    def _ensure_backends_initialized(self) -> None:
        """Lazily initialize backend services."""
        if self._word_converter is None:
            config = self.config_manager.get_config()
            # Determine preferred backend from config
            preferred_backend = None
            if config.preferred_conversion_backend == "word":
                preferred_backend = ConversionBackendType.WORD
            elif config.preferred_conversion_backend == "libreoffice":
                preferred_backend = ConversionBackendType.LIBREOFFICE
            # auto: leave as None for automatic selection

            libreoffice_path = config.libreoffice_path if config.libreoffice_path else None
            self._word_converter = WordConverter(
                preferred_backend=preferred_backend,
                libreoffice_path=libreoffice_path
            )
        if self._gs_wrapper is None:
            config = self.config_manager.get_config()
            gs_path = config.ghostscript_path if config.ghostscript_path else None
            self._gs_wrapper = GhostscriptWrapper(gs_path=gs_path)
        if self._pdf_labeler is None:
            self._pdf_labeler = PDFLabeler()

    def _ensure_engines_initialized(self) -> None:
        """Lazily initialize processing engines."""
        self._ensure_backends_initialized()
        if self._conversion_engine is None:
            self._conversion_engine = ConversionEngine(self._word_converter)
        if self._compression_engine is None:
            self._compression_engine = CompressionEngine(self._gs_wrapper)
        if self._labeling_engine is None:
            self._labeling_engine = LabelingEngine(self._pdf_labeler)

    @property
    def is_processing(self) -> bool:
        """Check if an operation is currently in progress."""
        return self._is_processing

    def set_callbacks(self,
                     progress_callback: Optional[Callable[[int, int, str], None]] = None,
                     completion_callback: Optional[Callable[[ProcessingResults], None]] = None,
                     error_callback: Optional[Callable[[str], None]] = None) -> None:
        """Set callbacks for progress updates, completion, and errors.

        Args:
            progress_callback: Called with (current, total, filename) during processing
            completion_callback: Called with ProcessingResults when operation completes
            error_callback: Called with error message when an error occurs
        """
        self._progress_callback = progress_callback
        self._completion_callback = completion_callback
        self._error_callback = error_callback

    def get_settings(self) -> Dict[str, Any]:
        """Get current settings as a dictionary.

        Returns:
            Dict containing all current configuration settings
        """
        config = self.config_manager.get_config()
        return asdict(config)

    def update_settings(self, **kwargs) -> bool:
        """Update specific settings.

        Args:
            **kwargs: Settings to update

        Returns:
            bool: True if settings were updated successfully
        """
        try:
            self.config_manager.update_config(**kwargs)
            self.logger.info(f"Settings updated: {list(kwargs.keys())}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update settings: {e}")
            if self._error_callback:
                self._error_callback(str(e))
            return False

    def reset_settings(self) -> bool:
        """Reset all settings to defaults.

        Returns:
            bool: True if reset was successful
        """
        try:
            self.config_manager.reset_to_defaults()
            self.logger.info("Settings reset to defaults")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset settings: {e}")
            if self._error_callback:
                self._error_callback(str(e))
            return False

    def request_cancel(self) -> None:
        """Request cancellation of the current operation."""
        if self._is_processing:
            self._cancel_requested = True
            self.logger.info("Cancellation requested")

    def _check_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_requested

    def _run_operation(self, operation_func: Callable,
                       files: List[str], output_dir: str,
                       settings: Dict[str, Any]) -> None:
        """Run an operation in a background thread.

        Args:
            operation_func: The engine function to call
            files: List of input files
            output_dir: Output directory
            settings: Processing settings
        """
        try:
            self._is_processing = True
            self._cancel_requested = False

            def progress_wrapper(current: int, total: int, filename: str) -> None:
                if self._cancel_requested:
                    raise InterruptedError("Operation cancelled")
                if self._progress_callback:
                    self._progress_callback(current, total, filename)

            results = operation_func(files, output_dir, settings, progress_wrapper)

            if self._completion_callback:
                self._completion_callback(results)

        except InterruptedError:
            self.logger.info("Operation was cancelled")
            # Create partial results indicating cancellation
            results = ProcessingResults()
            if self._completion_callback:
                self._completion_callback(results)
        except Exception as e:
            self.logger.error(f"Operation failed: {e}")
            if self._error_callback:
                error_msg = str(e)
                if self.error_handler:
                    error_msg = self.error_handler.handle_error(e, "Processing")
                self._error_callback(error_msg)
        finally:
            self._is_processing = False
            self._cancel_requested = False

    def start_conversion(self, files: List[str], output_dir: str,
                        settings: Optional[Dict[str, Any]] = None) -> bool:
        """Start Word to PDF conversion.

        Args:
            files: List of Word document paths
            output_dir: Output directory for PDFs
            settings: Optional settings override (uses config if None)

        Returns:
            bool: True if operation was started successfully
        """
        if self._is_processing:
            self.logger.warning("Cannot start conversion: operation already in progress")
            return False

        self._ensure_engines_initialized()

        if settings is None:
            settings = self.get_settings()

        self.logger.info(f"Starting conversion of {len(files)} files to {output_dir}")

        self._current_operation = threading.Thread(
            target=self._run_operation,
            args=(self._conversion_engine.convert_files, files, output_dir, settings),
            daemon=True
        )
        self._current_operation.start()
        return True

    def start_compression(self, files: List[str], output_dir: str,
                         settings: Optional[Dict[str, Any]] = None) -> bool:
        """Start PDF compression.

        Args:
            files: List of PDF file paths
            output_dir: Output directory for compressed PDFs
            settings: Optional settings override (uses config if None)

        Returns:
            bool: True if operation was started successfully
        """
        if self._is_processing:
            self.logger.warning("Cannot start compression: operation already in progress")
            return False

        self._ensure_engines_initialized()

        if settings is None:
            settings = self.get_settings()

        self.logger.info(f"Starting compression of {len(files)} files to {output_dir}")

        self._current_operation = threading.Thread(
            target=self._run_operation,
            args=(self._compression_engine.compress_files, files, output_dir, settings),
            daemon=True
        )
        self._current_operation.start()
        return True

    def start_labeling(self, files: List[str], output_dir: str,
                      settings: Optional[Dict[str, Any]] = None) -> bool:
        """Start PDF labeling.

        Args:
            files: List of PDF file paths
            output_dir: Output directory for labeled PDFs
            settings: Optional settings override (uses config if None)

        Returns:
            bool: True if operation was started successfully
        """
        if self._is_processing:
            self.logger.warning("Cannot start labeling: operation already in progress")
            return False

        self._ensure_engines_initialized()

        if settings is None:
            settings = self.get_settings()

        self.logger.info(f"Starting labeling of {len(files)} files to {output_dir}")

        self._current_operation = threading.Thread(
            target=self._run_operation,
            args=(self._labeling_engine.label_files, files, output_dir, settings),
            daemon=True
        )
        self._current_operation.start()
        return True

    def generate_label_preview(self, input_path: str,
                               settings: Optional[Dict[str, Any]] = None,
                               page_num: int = 0) -> Optional[bytes]:
        """Generate a preview of label placement.

        Args:
            input_path: Path to input PDF
            settings: Optional settings override
            page_num: Page number to preview (0-indexed)

        Returns:
            PNG image bytes or None if preview generation fails
        """
        try:
            self._ensure_engines_initialized()

            if settings is None:
                settings = self.get_settings()

            return self._labeling_engine.generate_preview(input_path, settings, page_num=page_num)
        except Exception as e:
            self.logger.error(f"Failed to generate preview: {e}")
            if self._error_callback:
                self._error_callback(str(e))
            return None

    def get_pdf_page_count(self, input_path: str) -> int:
        """Get the total number of pages in a PDF file.

        Args:
            input_path: Path to PDF file

        Returns:
            Number of pages, or 0 if the file cannot be read
        """
        try:
            import fitz
            doc = fitz.open(input_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            self.logger.error(f"Failed to get page count: {e}")
            return 0

    def validate_files(self, files: List[str], file_type: str = "any") -> Dict[str, Any]:
        """Validate a list of files.

        Args:
            files: List of file paths to validate
            file_type: Expected file type ("word", "pdf", or "any")

        Returns:
            Dict with 'valid_files', 'invalid_files', and 'errors' keys
        """
        from pathlib import Path

        valid_files = []
        invalid_files = []
        errors = []

        word_extensions = {'.doc', '.docx', '.rtf'}
        pdf_extensions = {'.pdf'}

        for file_path in files:
            path = Path(file_path)

            if not path.exists():
                invalid_files.append(file_path)
                errors.append(f"File not found: {file_path}")
                continue

            if not path.is_file():
                invalid_files.append(file_path)
                errors.append(f"Not a file: {file_path}")
                continue

            ext = path.suffix.lower()

            if file_type == "word":
                if ext in word_extensions:
                    valid_files.append(file_path)
                else:
                    invalid_files.append(file_path)
                    errors.append(f"Not a Word document: {file_path}")
            elif file_type == "pdf":
                if ext in pdf_extensions:
                    valid_files.append(file_path)
                else:
                    invalid_files.append(file_path)
                    errors.append(f"Not a PDF file: {file_path}")
            else:
                # Any file type
                valid_files.append(file_path)

        return {
            'valid_files': valid_files,
            'invalid_files': invalid_files,
            'errors': errors
        }

    def check_dependencies(self) -> Dict[str, Any]:
        """Check if all required dependencies are available.

        Returns:
            Dict with dependency status information
        """
        status = {
            'ghostscript': {'available': False, 'path': None, 'error': None},
            'docx2pdf': {'available': False, 'error': None},
            'pymupdf': {'available': False, 'error': None},
            'libreoffice': {'available': False, 'path': None, 'error': None}
        }

        # Check Ghostscript
        try:
            self._ensure_backends_initialized()
            if self._gs_wrapper.gs_path:
                status['ghostscript']['available'] = True
                status['ghostscript']['path'] = self._gs_wrapper.gs_path
        except Exception as e:
            status['ghostscript']['error'] = str(e)

        # Check docx2pdf
        try:
            import docx2pdf
            status['docx2pdf']['available'] = True
        except ImportError as e:
            status['docx2pdf']['error'] = str(e)

        # Check PyMuPDF
        try:
            import fitz
            status['pymupdf']['available'] = True
        except ImportError as e:
            status['pymupdf']['error'] = str(e)

        # Check LibreOffice
        try:
            from ..backend.libreoffice_installer import LibreOfficeInstaller
            installer = LibreOfficeInstaller()
            lo_path = installer.detect_libreoffice()
            if lo_path:
                status['libreoffice']['available'] = True
                status['libreoffice']['path'] = lo_path
        except Exception as e:
            status['libreoffice']['error'] = str(e)

        return status

    def check_and_setup_ghostscript(self) -> bool:
        """Check if Ghostscript is available.

        Returns:
            bool: True if Ghostscript is available
        """
        self._ensure_backends_initialized()
        return self._gs_wrapper.is_available()

    def refresh_ghostscript(self, gs_path: Optional[str] = None) -> None:
        """Re-initialize Ghostscript wrapper after install or path change.

        Args:
            gs_path: Optional explicit path to set
        """
        if gs_path:
            self.update_settings(ghostscript_path=gs_path)
        # Force re-initialization on next use
        self._gs_wrapper = None

    def get_conversion_backend_status(self) -> Dict[str, Any]:
        """Get detailed status of Word to PDF conversion backends.

        Returns:
            Dict with backend status information
        """
        self._ensure_backends_initialized()
        return self._word_converter.get_backend_status()

    def refresh_libreoffice(self, lo_path: Optional[str] = None) -> None:
        """Re-initialize WordConverter after LibreOffice install or path change.

        Args:
            lo_path: Optional explicit path to set
        """
        if lo_path:
            self.update_settings(libreoffice_path=lo_path)
        # Force re-initialization on next use
        self._word_converter = None
        self._conversion_engine = None

    def get_text(self, key: str, **kwargs) -> str:
        """Get localized text.

        Args:
            key: Translation key
            **kwargs: Format arguments

        Returns:
            Translated text or key if not found
        """
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def set_language(self, language_code: str) -> bool:
        """Change the application language.

        Args:
            language_code: Language code (e.g., 'en', 'zh')

        Returns:
            bool: True if language was changed successfully
        """
        if self.language_manager:
            return self.language_manager.set_language(language_code)
        return False
