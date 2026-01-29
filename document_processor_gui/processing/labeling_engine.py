import time
import os
import logging
import concurrent.futures
from typing import List, Callable, Optional, Dict, Any
from pathlib import Path
from ..backend.pdf_labeler import PDFLabeler
from .models import ProcessingResult, ProcessingResults

class LabelingEngine:
    """Engine for PDF labeling."""
    
    def __init__(self, pdf_labeler: PDFLabeler):
        self.logger = logging.getLogger(__name__)
        self.pdf_labeler = pdf_labeler

    def label_files(self, files: List[str], output_dir: str, 
                   settings: Dict[str, Any], 
                   progress_callback: Optional[Callable[[int, int, str], None]] = None) -> ProcessingResults:
        """
        Label multiple PDF files.
        
        Args:
            files: List of input file paths
            output_dir: Directory for output files
            settings: Dictionary of labeling settings
            progress_callback: Callback(current, total, message)
            
        Returns:
            ProcessingResults: Results of the operation
        """
        results = ProcessingResults()
        total = len(files)
        
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        tasks = []
        for file_path in files:
            tasks.append((file_path, output_dir, settings))

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
            input_file=str(input_path),
            file_size_before=input_path.stat().st_size if input_path.exists() else 0
        )
        
        try:
            if not input_path.exists():
                result.error_message = "File not found"
            else:
                # Determine label text: use settings 'label_text' if constant, otherwise filename
                # If include_path is True, use full path?
                # For now, default to filename as per requirement
                label_text = settings.get('label_text')
                if not label_text:
                    if settings.get('include_path_in_label', False):
                        label_text = str(input_path)
                    else:
                        label_text = input_path.name
                
                success = self.pdf_labeler.add_label(
                    str(input_path),
                    str(output_path),
                    text=label_text,
                    position=settings.get('label_position', 'footer'),
                    font_size=settings.get('label_font_size', 10),
                    color=settings.get('label_font_color', '#FF0000'),
                    opacity=settings.get('label_transparency', 1.0),
                    font_path=settings.get('font_path')
                )
                
                result.success = success
                if success:
                    result.output_file = str(output_path)
                    if output_path.exists():
                        result.file_size_after = output_path.stat().st_size
                else:
                    result.error_message = "Labeling failed"
                    
        except Exception as e:
            result.error_message = str(e)
            
        result.processing_time = time.time() - start_time
        return result
        
    def generate_preview(self, input_path: str, settings: Dict[str, Any]) -> bytes:
        """Generate preview for labeling."""
        input_path = Path(input_path)
        label_text = settings.get('label_text')
        if not label_text:
            if settings.get('include_path_in_label', False):
                label_text = str(input_path)
            else:
                label_text = input_path.name
                
        return self.pdf_labeler.generate_preview(
            str(input_path),
            text=label_text,
            position=settings.get('label_position', 'footer'),
            font_size=settings.get('label_font_size', 10),
            color=settings.get('label_font_color', '#FF0000'),
            opacity=settings.get('label_transparency', 1.0)
        )
