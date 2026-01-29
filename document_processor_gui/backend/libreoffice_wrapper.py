"""LibreOffice wrapper for Word to PDF conversion."""

import subprocess
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from ..core.exceptions import ProcessingError, DependencyError, FileSystemError


class LibreOfficeWrapper:
    """Wrapper for LibreOffice headless conversion."""

    def __init__(self, soffice_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.soffice_path = soffice_path
        if not self.soffice_path:
            self.soffice_path = self._find_libreoffice()

    def _find_libreoffice(self) -> Optional[str]:
        """Find LibreOffice executable."""
        if self.soffice_path and Path(self.soffice_path).is_file():
            return self.soffice_path

        from .libreoffice_installer import LibreOfficeInstaller
        installer = LibreOfficeInstaller()
        return installer.detect_libreoffice()

    def is_available(self) -> bool:
        """Check if LibreOffice is available."""
        return self.soffice_path is not None

    def get_version(self) -> str:
        """Get LibreOffice version."""
        if not self.soffice_path:
            return "Not found"

        try:
            result = subprocess.run(
                [self.soffice_path, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception as e:
            self.logger.warning(f"Failed to get LibreOffice version: {e}")
            return "Unknown"

    def convert_to_pdf(self, input_path: str, output_path: str) -> bool:
        """
        Convert Word document to PDF using LibreOffice.

        Args:
            input_path: Input Word document path
            output_path: Output PDF path

        Returns:
            bool: True if successful

        Raises:
            DependencyError: If LibreOffice is not found
            ProcessingError: If conversion fails
            FileSystemError: If file access fails
        """
        if not self.soffice_path:
            raise DependencyError("LibreOffice not found", dependency="libreoffice")

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileSystemError("Input file not found", file_path=str(input_path))

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # LibreOffice creates output with same stem as input, so we may need to rename
        expected_pdf_name = input_path.stem + ".pdf"

        # Use temporary directory as output to avoid issues with LibreOffice output naming
        with tempfile.TemporaryDirectory(prefix="lo_convert_") as temp_dir:
            try:
                cmd = [
                    self.soffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", temp_dir,
                    str(input_path)
                ]

                self.logger.info(f"Running LibreOffice: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=300,  # 5 minutes timeout
                    encoding="utf-8",
                    errors="ignore"
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    self.logger.error(f"LibreOffice failed: {error_msg}")
                    raise ProcessingError(
                        f"Conversion failed: {error_msg}",
                        file_path=str(input_path)
                    )

                # Move the output file to desired location
                temp_pdf = Path(temp_dir) / expected_pdf_name
                if temp_pdf.exists():
                    shutil.move(str(temp_pdf), str(output_path))
                    self.logger.info(f"Successfully converted {input_path}")
                    return True
                else:
                    # Check for any PDF file in temp dir
                    pdf_files = list(Path(temp_dir).glob("*.pdf"))
                    if pdf_files:
                        shutil.move(str(pdf_files[0]), str(output_path))
                        self.logger.info(f"Successfully converted {input_path}")
                        return True
                    else:
                        raise ProcessingError(
                            "LibreOffice did not produce output PDF",
                            file_path=str(input_path)
                        )

            except subprocess.TimeoutExpired:
                raise ProcessingError(
                    "LibreOffice conversion timed out",
                    file_path=str(input_path)
                )
            except OSError as e:
                raise ProcessingError(
                    f"Failed to execute LibreOffice: {e}",
                    file_path=str(input_path)
                )
            except Exception as e:
                if isinstance(e, (ProcessingError, DependencyError, FileSystemError)):
                    raise
                self.logger.error(f"Unexpected error during conversion: {e}")
                raise ProcessingError(f"Unexpected error: {str(e)}", file_path=str(input_path))
