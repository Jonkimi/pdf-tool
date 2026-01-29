"""Input validation system for document processing."""

import os
import shutil
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from enum import Enum


class ValidationSeverity(Enum):
    """Severity level of validation issues."""
    ERROR = "error"      # Prevents processing
    WARNING = "warning"  # May affect results
    INFO = "info"        # Informational only


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: ValidationSeverity
    message: str
    file_path: Optional[str] = None
    field: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'severity': self.severity.value,
            'message': self.message,
            'file_path': self.file_path,
            'field': self.field,
            'suggestion': self.suggestion
        }


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(self, message: str, file_path: Optional[str] = None,
                  field: Optional[str] = None, suggestion: Optional[str] = None):
        """Add an error issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message=message,
            file_path=file_path,
            field=field,
            suggestion=suggestion
        ))
        self.is_valid = False

    def add_warning(self, message: str, file_path: Optional[str] = None,
                    field: Optional[str] = None, suggestion: Optional[str] = None):
        """Add a warning issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            message=message,
            file_path=file_path,
            field=field,
            suggestion=suggestion
        ))

    def add_info(self, message: str, file_path: Optional[str] = None,
                 field: Optional[str] = None, suggestion: Optional[str] = None):
        """Add an info issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            message=message,
            file_path=file_path,
            field=field,
            suggestion=suggestion
        ))

    def merge(self, other: "ValidationResult"):
        """Merge another validation result into this one."""
        self.issues.extend(other.issues)
        if not other.is_valid:
            self.is_valid = False

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all error issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warning issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def get_summary(self) -> str:
        """Get a summary of validation issues."""
        error_count = len(self.errors)
        warning_count = len(self.warnings)

        if error_count == 0 and warning_count == 0:
            return "Validation passed"
        elif error_count > 0:
            return f"Validation failed: {error_count} error(s), {warning_count} warning(s)"
        else:
            return f"Validation passed with {warning_count} warning(s)"


class InputValidator:
    """Validates input files and settings for processing."""

    # Supported file extensions
    WORD_EXTENSIONS = {'.doc', '.docx', '.rtf'}
    PDF_EXTENSIONS = {'.pdf'}

    # Size limits (in bytes)
    MIN_FILE_SIZE = 1  # 1 byte minimum
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB maximum
    WARN_FILE_SIZE = 100 * 1024 * 1024  # Warn above 100 MB

    def __init__(self):
        """Initialize validator."""
        self.logger = logging.getLogger(__name__)

    def validate_file(self, file_path: str, expected_type: str = "any") -> ValidationResult:
        """Validate a single file.

        Args:
            file_path: Path to file
            expected_type: Expected file type ('word', 'pdf', or 'any')

        Returns:
            ValidationResult
        """
        result = ValidationResult()
        path = Path(file_path)

        # Check existence
        if not path.exists():
            result.add_error(
                "File does not exist",
                file_path=file_path,
                suggestion="Check file path or select a different file"
            )
            return result

        # Check is file (not directory)
        if not path.is_file():
            result.add_error(
                "Path is not a file",
                file_path=file_path,
                suggestion="Select a file, not a directory"
            )
            return result

        # Check readability
        if not os.access(path, os.R_OK):
            result.add_error(
                "File is not readable (permission denied)",
                file_path=file_path,
                suggestion="Check file permissions or run with elevated privileges"
            )
            return result

        # Check extension
        ext = path.suffix.lower()
        if expected_type == "word":
            if ext not in self.WORD_EXTENSIONS:
                result.add_error(
                    f"Invalid file type: {ext}. Expected Word document",
                    file_path=file_path,
                    suggestion=f"Supported formats: {', '.join(self.WORD_EXTENSIONS)}"
                )
        elif expected_type == "pdf":
            if ext not in self.PDF_EXTENSIONS:
                result.add_error(
                    f"Invalid file type: {ext}. Expected PDF",
                    file_path=file_path,
                    suggestion="Convert to PDF format first"
                )

        # Check file size
        try:
            size = path.stat().st_size
            if size < self.MIN_FILE_SIZE:
                result.add_error(
                    "File is empty or too small",
                    file_path=file_path,
                    suggestion="Select a valid file with content"
                )
            elif size > self.MAX_FILE_SIZE:
                result.add_error(
                    f"File is too large ({size / (1024*1024):.1f} MB)",
                    file_path=file_path,
                    suggestion=f"Maximum supported size is {self.MAX_FILE_SIZE / (1024*1024):.0f} MB"
                )
            elif size > self.WARN_FILE_SIZE:
                result.add_warning(
                    f"Large file ({size / (1024*1024):.1f} MB) may take longer to process",
                    file_path=file_path
                )
        except OSError as e:
            result.add_error(
                f"Cannot read file metadata: {e}",
                file_path=file_path
            )

        # Check file integrity (basic check)
        if ext == '.pdf':
            integrity_result = self._check_pdf_integrity(file_path)
            result.merge(integrity_result)
        elif ext == '.docx':
            integrity_result = self._check_docx_integrity(file_path)
            result.merge(integrity_result)

        return result

    def validate_files(self, files: List[str], expected_type: str = "any") -> ValidationResult:
        """Validate multiple files.

        Args:
            files: List of file paths
            expected_type: Expected file type

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not files:
            result.add_error(
                "No files provided",
                suggestion="Select at least one file to process"
            )
            return result

        for file_path in files:
            file_result = self.validate_file(file_path, expected_type)
            result.merge(file_result)

        return result

    def validate_output_directory(self, directory: str,
                                  required_space: int = 0) -> ValidationResult:
        """Validate output directory.

        Args:
            directory: Output directory path
            required_space: Minimum required space in bytes

        Returns:
            ValidationResult
        """
        result = ValidationResult()
        path = Path(directory)

        # Check if path is provided
        if not directory:
            result.add_error(
                "No output directory specified",
                suggestion="Select an output directory"
            )
            return result

        # Check if directory exists or can be created
        if path.exists():
            if not path.is_dir():
                result.add_error(
                    "Output path exists but is not a directory",
                    file_path=directory,
                    suggestion="Select a different output location"
                )
                return result

            if not os.access(path, os.W_OK):
                result.add_error(
                    "Output directory is not writable",
                    file_path=directory,
                    suggestion="Check permissions or select a different directory"
                )
                return result
        else:
            # Try to determine if we can create it
            parent = path.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                result.add_error(
                    "Cannot create output directory (permission denied)",
                    file_path=directory,
                    suggestion="Select a different location"
                )
                return result

        # Check available disk space
        if required_space > 0:
            try:
                # Get the disk space for the target or its parent
                check_path = path if path.exists() else path.parent
                if check_path.exists():
                    disk_usage = shutil.disk_usage(check_path)
                    if disk_usage.free < required_space:
                        result.add_error(
                            f"Insufficient disk space. Need {required_space / (1024*1024):.1f} MB, "
                            f"have {disk_usage.free / (1024*1024):.1f} MB",
                            file_path=directory,
                            suggestion="Free up disk space or select a different drive"
                        )
                    elif disk_usage.free < required_space * 2:
                        result.add_warning(
                            "Low disk space. Processing may fail if output is larger than expected",
                            file_path=directory
                        )
            except OSError as e:
                result.add_warning(
                    f"Cannot check disk space: {e}",
                    file_path=directory
                )

        return result

    def validate_settings(self, settings: Dict[str, Any],
                         processing_type: str) -> ValidationResult:
        """Validate processing settings.

        Args:
            settings: Settings dictionary
            processing_type: Type of processing ('conversion', 'compression', 'labeling')

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Common validations
        if processing_type == "compression":
            # Compression quality
            quality = settings.get('compression_quality', 'ebook')
            valid_qualities = ['screen', 'ebook', 'printer', 'prepress']
            if quality not in valid_qualities:
                result.add_error(
                    f"Invalid compression quality: {quality}",
                    field='compression_quality',
                    suggestion=f"Use one of: {', '.join(valid_qualities)}"
                )

            # DPI
            dpi = settings.get('target_dpi', 144)
            if not isinstance(dpi, int) or dpi < 72 or dpi > 600:
                result.add_error(
                    f"Invalid DPI value: {dpi}",
                    field='target_dpi',
                    suggestion="DPI must be between 72 and 600"
                )

        elif processing_type == "labeling":
            # Font size
            font_size = settings.get('label_font_size', 10)
            if not isinstance(font_size, int) or font_size < 6 or font_size > 72:
                result.add_error(
                    f"Invalid font size: {font_size}",
                    field='label_font_size',
                    suggestion="Font size must be between 6 and 72"
                )

            # Position
            position = settings.get('label_position', 'footer')
            valid_positions = ['header', 'footer', 'top-left', 'top-right', 'bottom-left', 'bottom-right']
            if position not in valid_positions:
                result.add_error(
                    f"Invalid label position: {position}",
                    field='label_position',
                    suggestion=f"Use one of: {', '.join(valid_positions)}"
                )

            # Color format
            color = settings.get('label_font_color', '#FF0000')
            if not self._is_valid_hex_color(color):
                result.add_error(
                    f"Invalid color format: {color}",
                    field='label_font_color',
                    suggestion="Use hex color format (e.g., #FF0000)"
                )

            # Transparency
            transparency = settings.get('label_transparency', 1.0)
            if not isinstance(transparency, (int, float)) or transparency < 0 or transparency > 1:
                result.add_error(
                    f"Invalid transparency: {transparency}",
                    field='label_transparency',
                    suggestion="Transparency must be between 0.0 and 1.0"
                )

        elif processing_type == "conversion":
            # Image quality
            quality = settings.get('image_quality', 75)
            if not isinstance(quality, int) or quality < 1 or quality > 100:
                result.add_error(
                    f"Invalid image quality: {quality}",
                    field='image_quality',
                    suggestion="Image quality must be between 1 and 100"
                )

        return result

    def validate_dependencies(self) -> ValidationResult:
        """Validate that required dependencies are available.

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Check PyMuPDF
        try:
            import fitz
            result.add_info("PyMuPDF is available")
        except ImportError:
            result.add_error(
                "PyMuPDF is not installed",
                suggestion="Install with: pip install pymupdf"
            )

        # Check PIL
        try:
            from PIL import Image
            result.add_info("Pillow is available")
        except ImportError:
            result.add_warning(
                "Pillow is not installed - preview features may be limited",
                suggestion="Install with: pip install pillow"
            )

        # Check Ghostscript
        from ..backend.ghostscript_wrapper import GhostscriptWrapper
        try:
            gs = GhostscriptWrapper()
            if gs.gs_path:
                result.add_info(f"Ghostscript found at: {gs.gs_path}")
            else:
                result.add_warning(
                    "Ghostscript not found - PDF compression will not work",
                    suggestion="Install Ghostscript from https://ghostscript.com/"
                )
        except Exception as e:
            result.add_warning(
                f"Could not check Ghostscript: {e}",
                suggestion="Ensure Ghostscript is installed for PDF compression"
            )

        return result

    def _check_pdf_integrity(self, file_path: str) -> ValidationResult:
        """Check PDF file integrity."""
        result = ValidationResult()

        try:
            import fitz
            doc = fitz.open(file_path)
            page_count = len(doc)

            if page_count == 0:
                result.add_error(
                    "PDF has no pages",
                    file_path=file_path
                )
            elif page_count > 1000:
                result.add_warning(
                    f"PDF has many pages ({page_count}), processing may be slow",
                    file_path=file_path
                )

            doc.close()

        except ImportError:
            pass  # PyMuPDF not available, skip check
        except Exception as e:
            result.add_error(
                f"PDF appears to be corrupted or encrypted: {e}",
                file_path=file_path,
                suggestion="Ensure the PDF is valid and not password-protected"
            )

        return result

    def _check_docx_integrity(self, file_path: str) -> ValidationResult:
        """Check DOCX file integrity."""
        result = ValidationResult()

        try:
            import zipfile
            # DOCX is a ZIP file, so we can check if it's valid
            if not zipfile.is_zipfile(file_path):
                result.add_error(
                    "DOCX file appears to be corrupted",
                    file_path=file_path,
                    suggestion="Try opening and re-saving the file in Word"
                )
        except Exception as e:
            result.add_warning(
                f"Could not verify DOCX integrity: {e}",
                file_path=file_path
            )

        return result

    def _is_valid_hex_color(self, color: str) -> bool:
        """Check if string is valid hex color."""
        if not color:
            return False
        if not color.startswith('#'):
            return False
        hex_part = color[1:]
        if len(hex_part) not in (3, 6):
            return False
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False

    def estimate_output_size(self, files: List[str],
                            processing_type: str,
                            settings: Dict[str, Any]) -> int:
        """Estimate required output space.

        Args:
            files: Input files
            processing_type: Type of processing
            settings: Processing settings

        Returns:
            Estimated output size in bytes
        """
        total_input_size = 0
        for file_path in files:
            try:
                total_input_size += Path(file_path).stat().st_size
            except OSError:
                pass

        # Estimation factors based on processing type
        if processing_type == "compression":
            quality = settings.get('compression_quality', 'ebook')
            factors = {
                'screen': 0.3,
                'ebook': 0.5,
                'printer': 0.7,
                'prepress': 0.9
            }
            factor = factors.get(quality, 0.5)
            return int(total_input_size * factor * 1.2)  # 20% buffer

        elif processing_type == "conversion":
            # PDF usually larger than Word
            return int(total_input_size * 1.5)

        elif processing_type == "labeling":
            # Labels add minimal size
            return int(total_input_size * 1.05)

        return total_input_size
