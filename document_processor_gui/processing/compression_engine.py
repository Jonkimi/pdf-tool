import time
import os
import logging
import concurrent.futures
from typing import List, Callable, Optional, Dict, Any
from pathlib import Path
from ..backend.ghostscript_wrapper import GhostscriptWrapper
from .models import ProcessingResult, ProcessingResults

class CompressionEngine:
    """Engine for PDF compression."""
    
    def __init__(self, gs_wrapper: GhostscriptWrapper):
        self.logger = logging.getLogger(__name__)
        self.gs_wrapper = gs_wrapper

    def compress_files(self, files: List[str], output_dir: str, 
                      settings: Dict[str, Any], 
                      progress_callback: Optional[Callable[[int, int, str], None]] = None) -> ProcessingResults:
        """
        Compress multiple PDF files.
        
        Args:
            files: List of input file paths
            output_dir: Directory for output files
            settings: Dictionary of compression settings
            progress_callback: Callback(current, total, message)
            
        Returns:
            ProcessingResults: Results of the operation
        """
        results = ProcessingResults()
        total = len(files)
        
        # Ensure output dir exists
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Prepare tasks
        tasks = []
        for file_path in files:
            tasks.append((file_path, output_dir, settings))

        # Use ThreadPoolExecutor since GS runs as subprocess
        max_workers = settings.get('max_concurrent_operations', os.cpu_count() or 2)
        
        completed_count = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_single_file, task): task[0] 
                for task in tasks
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                completed_count += 1
                
                if progress_callback:
                    progress_callback(completed_count, total, Path(file_path).name)
                
                try:
                    result = future.result()
                    results.add_result(result)
                except Exception as e:
                    self.logger.error(f"Error getting result for {file_path}: {e}")
                    result = ProcessingResult(
                        success=False,
                        input_file=file_path,
                        error_message=str(e)
                    )
                    results.add_result(result)
                    
        return results

    def _process_single_file(self, args) -> ProcessingResult:
        file_path, output_dir, settings = args
        start_time = time.time()
        input_path = Path(file_path)
        output_path = Path(output_dir) / input_path.name
        
        result = ProcessingResult(
            success=False,
            input_file=file_path,
            file_size_before=input_path.stat().st_size if input_path.exists() else 0
        )
        
        try:
            if not input_path.exists():
                result.error_message = "File not found"
            else:
                success = self.gs_wrapper.compress_pdf(
                    str(input_path),
                    str(output_path),
                    quality_preset=settings.get('compression_quality', 'ebook'),
                    target_dpi=settings.get('target_dpi', 144),
                    image_quality=settings.get('image_quality', 75),
                    downsample_threshold=settings.get('downsample_threshold', 1.1)
                )
                
                result.success = success
                if success:
                    result.output_file = str(output_path)
                    if output_path.exists():
                        result.file_size_after = output_path.stat().st_size
                else:
                    result.error_message = "Compression failed"
                    
        except Exception as e:
            result.error_message = str(e)
            
        result.processing_time = time.time() - start_time
        return result
