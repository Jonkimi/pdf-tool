import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional
from ..core.exceptions import ProcessingError, DependencyError, FileSystemError

class GhostscriptWrapper:
    """Wrapper for Ghostscript PDF compression."""
    
    def __init__(self, gs_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.gs_path = gs_path
        if not self.gs_path:
            self.gs_path = self._find_ghostscript()
        
    def _find_ghostscript(self) -> Optional[str]:
        """Find Ghostscript executable."""
        if self.gs_path and Path(self.gs_path).is_file():
            return self.gs_path

        from .ghostscript_installer import GhostscriptInstaller
        installer = GhostscriptInstaller()
        return installer.detect_ghostscript()

    def is_available(self) -> bool:
        """Check if Ghostscript is available."""
        return self.gs_path is not None

    def get_version(self) -> str:
        """Get Ghostscript version."""
        if not self.gs_path:
            return "Not found"
            
        try:
            result = subprocess.run(
                [self.gs_path, "--version"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except Exception as e:
            self.logger.warning(f"Failed to get GS version: {e}")
            return "Unknown"

    def compress_pdf(self, input_path: str, output_path: str,
                    quality_preset: str = "ebook",
                    target_dpi: int = 144,
                    image_quality: int = 75,
                    downsample_threshold: float = 1.1) -> bool:
        """
        Compress PDF using Ghostscript.

        Args:
            input_path: Input PDF path
            output_path: Output PDF path
            quality_preset: 'screen', 'ebook', 'printer', 'prepress' (Not used directly in this implementation but kept for interface compatibility)
            target_dpi: Target DPI for downsampling
            image_quality: JPEG quality (1-100)
            downsample_threshold: Downsample threshold (>=1.0, images with resolution > target_dpi * threshold will be downsampled)

        Returns:
            bool: True if successful

        Raises:
            DependencyError: If Ghostscript is not found
            ProcessingError: If compression fails
            FileSystemError: If file access fails
        """
        if not self.gs_path:
            raise DependencyError("Ghostscript not found", dependency="ghostscript")

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileSystemError("Input file not found", file_path=str(input_path))

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use provided threshold
        threshold = downsample_threshold
        
        # Build command based on logic in process_pdf.py but simplified/cleaned
        cmd = [
            self.gs_path,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.5",
            
            # Color Images
            "-dDownsampleColorImages=true",
            "-dColorImageDownsampleType=/Bicubic",
            f"-dColorImageResolution={target_dpi}",
            f"-dColorImageDownsampleThreshold={threshold}",
            "-dAutoFilterColorImages=false",
            "-dColorImageFilter=/DCTEncode",
            "-dEncodeColorImages=true",
            
            # Gray Images
            "-dDownsampleGrayImages=true",
            "-dGrayImageDownsampleType=/Bicubic",
            f"-dGrayImageResolution={target_dpi}",
            f"-dGrayImageDownsampleThreshold={threshold}",
            "-dAutoFilterGrayImages=false",
            "-dGrayImageFilter=/DCTEncode",
            "-dEncodeGrayImages=true",
            
            # Mono Images
            "-dDownsampleMonoImages=true",
            "-dMonoImageDownsampleType=/Subsample",
            f"-dMonoImageResolution={target_dpi * 2}",
            f"-dMonoImageDownsampleThreshold={threshold}",
            "-dMonoImageFilter=/CCITTFaxEncode",
            "-dEncodeMonoImages=true",
            
            # Quality
            f"-dJPEGQ={image_quality}",
            
            # Color conversion
            "-sColorConversionStrategy=RGB",
            "-dConvertCMYKImagesToRGB=true",
            "-sProcessColorModel=DeviceRGB",
            "-dOverrideICC=true",
            
            # Fonts and PDF structure
            "-dEmbedAllFonts=true",
            "-dSubsetFonts=true",
            "-dCompressFonts=true",
            "-dCompressStreams=true",
            "-dCompressPages=true",
            "-dDetectDuplicateImages=true",
            "-dOptimize=true",
            "-dUseFlateCompression=true",
            "-dFastWebView=true",
            
            "-dNOPAUSE",
            "-dBATCH",
            "-dQUIET",
            f"-sOutputFile={str(output_path)}",
            str(input_path)
        ]
        
        try:
            self.logger.info(f"Running Ghostscript: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="ignore"
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully compressed {input_path}")
                return True
            else:
                error_msg = result.stderr
                self.logger.error(f"Ghostscript failed: {error_msg}")
                raise ProcessingError(f"Compression failed: {error_msg}", file_path=str(input_path))
                
        except OSError as e:
            raise ProcessingError(f"Failed to execute Ghostscript: {e}", file_path=str(input_path))
        except Exception as e:
            if isinstance(e, (ProcessingError, DependencyError, FileSystemError)):
                raise
            self.logger.error(f"Unexpected error during compression: {e}")
            raise ProcessingError(f"Unexpected error: {str(e)}", file_path=str(input_path))
