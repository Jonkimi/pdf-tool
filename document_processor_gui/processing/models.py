from dataclasses import dataclass, field
from typing import Optional, List, Any

@dataclass
class ProcessingResult:
    success: bool
    input_file: str
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    file_size_before: int = 0
    file_size_after: Optional[int] = None

@dataclass
class ProcessingResults:
    results: List[ProcessingResult] = field(default_factory=list)
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_processing_time: float = 0.0
    
    def add_result(self, result: ProcessingResult):
        self.results.append(result)
        self.total_files += 1
        if result.success:
            self.successful_files += 1
        else:
            self.failed_files += 1
        self.total_processing_time += result.processing_time
            
    def get_summary(self) -> str:
        return f"Processed {self.total_files} files. Success: {self.successful_files}, Failed: {self.failed_files}"
    
    def get_failed_files(self) -> List[ProcessingResult]:
        return [r for r in self.results if not r.success]
