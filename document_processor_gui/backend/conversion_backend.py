"""Word to PDF conversion backend abstraction and hybrid strategy."""

import platform
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


class ConversionBackendType(Enum):
    """Available conversion backends."""
    WORD = auto()       # Microsoft Word via docx2pdf
    LIBREOFFICE = auto()  # LibreOffice headless


@dataclass
class BackendCapabilities:
    """Describes capabilities of a conversion backend."""
    platform_support: Tuple[str, ...]  # ("Windows", "Darwin", "Linux")
    name: str


class ConversionBackend(ABC):
    """Abstract base class for conversion backends."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available."""
        pass

    @abstractmethod
    def convert(self, input_path: str, output_path: str) -> bool:
        """Convert document to PDF."""
        pass

    @abstractmethod
    def get_capabilities(self) -> BackendCapabilities:
        """Get backend capabilities."""
        pass


class WordBackend(ConversionBackend):
    """Microsoft Word backend using docx2pdf."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._available: Optional[bool] = None

    def _detect_word_installation(self) -> bool:
        """Check if Microsoft Word is actually installed."""
        system = platform.system()

        if system == "Darwin":
            # macOS: check if Word.app exists
            word_app_path = Path("/Applications/Microsoft Word.app")
            return word_app_path.exists()

        elif system == "Windows":
            # Windows: try to access Word via COM
            try:
                import win32com.client
                word = win32com.client.Dispatch('Word.Application')
                word.Quit()
                return True
            except Exception:
                return False

        return False

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available

        system = platform.system()
        if system not in ("Windows", "Darwin"):
            self._available = False
            return False

        # Check if docx2pdf module is available
        try:
            from docx2pdf import convert  # noqa: F401
        except ImportError:
            self._available = False
            return False

        # Check if Word is actually installed
        self._available = self._detect_word_installation()
        return self._available

    def convert(self, input_path: str, output_path: str) -> bool:
        from docx2pdf import convert
        convert(input_path, output_path)
        return True

    def get_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            platform_support=("Windows", "Darwin"),
            name="Microsoft Word (docx2pdf)"
        )


class LibreOfficeBackend(ConversionBackend):
    """LibreOffice headless backend."""

    def __init__(self, soffice_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self._wrapper = None
        self._soffice_path = soffice_path

    def _ensure_wrapper(self):
        if self._wrapper is None:
            from .libreoffice_wrapper import LibreOfficeWrapper
            self._wrapper = LibreOfficeWrapper(soffice_path=self._soffice_path)

    def is_available(self) -> bool:
        self._ensure_wrapper()
        return self._wrapper.is_available()

    def convert(self, input_path: str, output_path: str) -> bool:
        self._ensure_wrapper()
        return self._wrapper.convert_to_pdf(input_path, output_path)

    def get_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            platform_support=("Windows", "Darwin", "Linux"),
            name="LibreOffice"
        )


class HybridConversionBackend:
    """
    Hybrid conversion backend with automatic fallback.

    Strategy:
    1. On Windows/macOS: Try Word first, fallback to LibreOffice
    2. On Linux: Use LibreOffice only
    """

    def __init__(self,
                 preferred_backend: Optional[ConversionBackendType] = None,
                 libreoffice_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self._preferred_backend = preferred_backend

        # Initialize backends
        self._word_backend = WordBackend()
        self._libreoffice_backend = LibreOfficeBackend(soffice_path=libreoffice_path)

        # Determine active backend
        self._active_backend: Optional[ConversionBackend] = None
        self._fallback_backend: Optional[ConversionBackend] = None
        self._select_backends()

    def _select_backends(self):
        """Select primary and fallback backends based on availability."""
        system = platform.system()

        if self._preferred_backend == ConversionBackendType.LIBREOFFICE:
            # User prefers LibreOffice
            if self._libreoffice_backend.is_available():
                self._active_backend = self._libreoffice_backend
                if self._word_backend.is_available():
                    self._fallback_backend = self._word_backend
        elif self._preferred_backend == ConversionBackendType.WORD:
            # User prefers Word
            if self._word_backend.is_available():
                self._active_backend = self._word_backend
                if self._libreoffice_backend.is_available():
                    self._fallback_backend = self._libreoffice_backend
        else:
            # Auto-select: prefer Word on supported platforms
            if system in ("Windows", "Darwin") and self._word_backend.is_available():
                self._active_backend = self._word_backend
                if self._libreoffice_backend.is_available():
                    self._fallback_backend = self._libreoffice_backend
            elif self._libreoffice_backend.is_available():
                self._active_backend = self._libreoffice_backend
                # No fallback on Linux from LibreOffice

    def is_available(self) -> bool:
        """Check if any backend is available."""
        return self._active_backend is not None

    def get_active_backend_name(self) -> str:
        """Get name of active backend."""
        if self._active_backend:
            return self._active_backend.get_capabilities().name
        return "None"

    def convert(self, input_path: str, output_path: str) -> bool:
        """
        Convert document to PDF using active backend with fallback.

        Args:
            input_path: Path to input document
            output_path: Path to output PDF

        Returns:
            bool: True if successful
        """
        if not self._active_backend:
            from ..core.exceptions import DependencyError
            raise DependencyError(
                "No conversion backend available. Please install Microsoft Word or LibreOffice.",
                dependency="word_or_libreoffice"
            )

        try:
            return self._active_backend.convert(input_path, output_path)
        except Exception as e:
            self.logger.warning(f"Primary backend failed: {e}")
            if self._fallback_backend:
                self.logger.info("Trying fallback backend...")
                return self._fallback_backend.convert(input_path, output_path)
            raise

    def get_backend_status(self) -> dict:
        """Get status of all backends."""
        return {
            "word": {
                "available": self._word_backend.is_available(),
                "capabilities": self._word_backend.get_capabilities().__dict__
            },
            "libreoffice": {
                "available": self._libreoffice_backend.is_available(),
                "capabilities": self._libreoffice_backend.get_capabilities().__dict__
            },
            "active_backend": self.get_active_backend_name(),
        }
