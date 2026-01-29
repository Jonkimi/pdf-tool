"""Word to PDF conversion with optional image compression."""

import os
import tempfile
import zipfile
import logging
from pathlib import Path
from typing import Optional, List
from PIL import Image
from .conversion_backend import HybridConversionBackend, ConversionBackendType
from ..core.exceptions import ProcessingError, ValidationError


class WordConverter:
    """Handles Word document to PDF conversion with optional image compression.

    Supports multiple backends:
    - Microsoft Word (via docx2pdf) on Windows/macOS
    - LibreOffice (headless) on all platforms

    Automatically selects the best available backend with fallback support.
    """

    SUPPORTED_FORMATS = ['.docx', '.doc']

    def __init__(self,
                 preferred_backend: Optional[ConversionBackendType] = None,
                 libreoffice_path: Optional[str] = None):
        """Initialize WordConverter.

        Args:
            preferred_backend: Preferred conversion backend (WORD, LIBREOFFICE, or None for auto)
            libreoffice_path: Custom path to LibreOffice executable
        """
        self.logger = logging.getLogger(__name__)
        self._backend = HybridConversionBackend(
            preferred_backend=preferred_backend,
            libreoffice_path=libreoffice_path
        )

    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        return Path(file_path).suffix.lower() in self.SUPPORTED_FORMATS

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file extensions."""
        return self.SUPPORTED_FORMATS

    def is_backend_available(self) -> bool:
        """Check if conversion backend is available."""
        return self._backend.is_available()

    def get_backend_name(self) -> str:
        """Get name of active conversion backend."""
        return self._backend.get_active_backend_name()

    def get_backend_status(self) -> dict:
        """Get detailed status of all backends."""
        return self._backend.get_backend_status()

    def convert_to_pdf(self, input_path: str, output_path: str,
                       image_compression_enabled: bool = False,
                       image_quality: int = 75,
                       optimize_png: bool = True) -> bool:
        """
        Convert Word document to PDF.

        Args:
            input_path: Path to input Word file
            output_path: Path to output PDF file
            image_compression_enabled: Whether to compress images inside docx
            image_quality: JPEG quality (1-100)
            optimize_png: Whether to optimize PNGs

        Returns:
            bool: True if successful

        Raises:
            ProcessingError: If conversion fails
            ValidationError: If input file is invalid
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise ValidationError("Input file does not exist", field="input_path", value=str(input_path))

        if not self.is_supported_format(str(input_path)):
            raise ValidationError("Unsupported file format", field="file_format", value=str(input_path))

        # Only .docx supports unzipping for image compression
        # .doc files need to be converted directly
        can_compress_images = input_path.suffix.lower() == '.docx'

        if image_compression_enabled and can_compress_images:
            return self._convert_with_compression(
                input_path, output_path, image_quality, optimize_png
            )
        else:
            if image_compression_enabled and not can_compress_images:
                self.logger.warning(f"Image compression not supported for {input_path.suffix}, converting directly.")
            return self._convert_directly(input_path, output_path)

    def _convert_directly(self, input_path: Path, output_path: Path) -> bool:
        """Convert directly using the hybrid backend."""
        try:
            self.logger.info(f"Converting {input_path} to {output_path} using {self.get_backend_name()}")
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            return self._backend.convert(str(input_path), str(output_path))
        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            raise ProcessingError(f"Conversion failed: {str(e)}", file_path=str(input_path))

    def _convert_with_compression(self, input_path: Path, output_path: Path,
                                  quality: int, optimize_png: bool) -> bool:
        """Unzip, compress images, rezip, then convert."""
        with tempfile.TemporaryDirectory(prefix="docx_proc_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            extracted_path = temp_dir / "extracted"
            modified_docx_path = temp_dir / f"compressed_{input_path.name}"

            try:
                # 1. Unzip
                self.logger.debug(f"Extracting {input_path}")
                with zipfile.ZipFile(input_path, "r") as zip_ref:
                    zip_ref.extractall(extracted_path)

                # 2. Compress images
                media_path = extracted_path / "word" / "media"
                if media_path.is_dir():
                    self._compress_images_in_folder(media_path, quality, optimize_png)

                # 3. Rezip
                self.logger.debug(f"Re-zipping to {modified_docx_path}")
                with zipfile.ZipFile(modified_docx_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(extracted_path):
                        arc_dir = Path(root).relative_to(extracted_path)
                        for file in files:
                            full_path = Path(root) / file
                            arc_name = (arc_dir / file).as_posix()
                            zipf.write(full_path, arcname=arc_name)

                # 4. Convert
                return self._convert_directly(modified_docx_path, output_path)

            except zipfile.BadZipFile:
                raise ProcessingError("Invalid docx file (not a zip)", file_path=str(input_path))
            except Exception as e:
                self.logger.error(f"Compression/Conversion failed: {e}")
                raise ProcessingError(f"Processing failed: {str(e)}", file_path=str(input_path))

    def _compress_images_in_folder(self, folder_path: Path, quality: int, optimize_png: bool):
        """Compress all images in the folder."""
        for item in folder_path.iterdir():
            if item.is_file() and item.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                try:
                    self._compress_single_image(item, quality, optimize_png)
                except Exception as e:
                    self.logger.warning(f"Failed to compress image {item.name}: {e}")

    def _compress_single_image(self, image_path: Path, quality: int, optimize_png: bool):
        """Compress a single image file."""
        try:
            with Image.open(image_path) as img:
                original_format = img.format
                if not original_format:
                    return

                if original_format.upper() in ["JPEG", "JPG"]:
                    if img.mode == "RGBA":
                        img = img.convert("RGB")
                    # Save overrides the file
                    img.save(image_path, "JPEG", quality=quality, optimize=True)

                elif original_format.upper() == "PNG" and optimize_png:
                    img.save(image_path, "PNG", optimize=True)
        except Exception as e:
            # Propagate error to caller
            raise e
