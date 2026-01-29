import time
import os
import logging
from typing import List, Callable, Optional, Dict, Any
from pathlib import Path
from ..backend.word_converter import WordConverter
from .models import ProcessingResult, ProcessingResults
from ..core.exceptions import ProcessingError

class ConversionEngine:
    """Engine for processing Word to PDF conversions."""
    
    def __init__(self, word_converter: WordConverter):
        self.logger = logging.getLogger(__name__)
        self.word_converter = word_converter

    def convert_files(self, files: List[str], output_dir: str, 
                     settings: Dict[str, Any], 
                     progress_callback: Optional[Callable[[int, int, str], None]] = None) -> ProcessingResults:
        """
        Convert multiple files to PDF.
        
        Args:
            files: List of input file paths
            output_dir: Directory for output files
            settings: Dictionary of conversion settings
            progress_callback: Callback(current, total, message)
            
        Returns:
            ProcessingResults: Results of the operation
        """
        results = ProcessingResults()
        total = len(files)
        
        # Ensure output dir exists
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create output directory {output_dir}: {e}")
            # If we can't create output dir, all will fail.
            # But we proceed loop to generate failure results or return early.
            # Returning early might be better but let's fail individually for consistency or raise exception?
            # Typically engine should not crash.
            pass
        
        for i, file_path in enumerate(files):
            # 1-based index for display, but i is 0-based
            current_idx = i + 1
            file_name = Path(file_path).name
            
            if progress_callback:
                progress_callback(current_idx, total, file_name)
            
            start_time = time.time()
            input_path = Path(file_path)
            
            # Determine output filename (preserve name, change suffix)
            output_filename = input_path.stem + ".pdf"
            output_path = Path(output_dir) / output_filename
            
            # Handle duplicates if needed? Overwrite for now.
            
            result = ProcessingResult(
                success=False,
                input_file=file_path,
                file_size_before=input_path.stat().st_size if input_path.exists() else 0
            )
            
            try:
                if not input_path.exists():
                    result.error_message = "File not found"
                else:
                    success = self.word_converter.convert_to_pdf(
                        str(input_path), 
                        str(output_path),
                        image_compression_enabled=settings.get('image_compression_enabled', False),
                        image_quality=settings.get('image_quality', 75),
                        optimize_png=settings.get('optimize_png', True)
                    )
                    
                    result.success = success
                    if success:
                        result.output_file = str(output_path)
                        if output_path.exists():
                            result.file_size_after = output_path.stat().st_size
                    else:
                        result.error_message = "Conversion returned False (unknown error)"
                    
            except Exception as e:
                self.logger.error(f"Error converting {file_path}: {e}")
                result.error_message = str(e)
            
            result.processing_time = time.time() - start_time
            results.add_result(result)
            
        return results
