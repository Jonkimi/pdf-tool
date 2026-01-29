"""Batch processing coordination module."""

import json
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime
from enum import Enum

from .models import ProcessingResults, ProcessingResult


class BatchMode(Enum):
    """Batch processing mode."""
    CONTINUE_ON_ERROR = "continue_on_error"  # Continue processing even if files fail
    STOP_ON_FAILURE = "stop_on_failure"      # Stop immediately on first failure


@dataclass
class BatchConfiguration:
    """Configuration for a batch processing job."""

    # Files to process
    files: List[str] = field(default_factory=list)

    # Output directory
    output_dir: str = ""

    # Processing type
    processing_type: str = "compression"  # conversion, compression, labeling

    # Processing settings
    settings: Dict[str, Any] = field(default_factory=dict)

    # Batch options
    mode: str = "continue_on_error"  # continue_on_error or stop_on_failure
    max_retries: int = 0  # Number of retries for failed files

    # Metadata
    name: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchConfiguration":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class BatchSummary:
    """Summary of a batch processing job."""

    # Job info
    name: str = ""
    processing_type: str = ""
    started_at: str = ""
    completed_at: str = ""

    # Statistics
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0

    # Timing
    total_time_seconds: float = 0.0
    average_time_per_file: float = 0.0

    # Size info (for compression)
    total_size_before: int = 0
    total_size_after: int = 0
    total_reduction_bytes: int = 0
    average_reduction_percent: float = 0.0

    # Details
    failed_file_details: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_report(self) -> str:
        """Generate a text report."""
        lines = [
            "=" * 60,
            f"Batch Processing Report: {self.name or 'Unnamed'}",
            "=" * 60,
            f"Processing Type: {self.processing_type}",
            f"Started: {self.started_at}",
            f"Completed: {self.completed_at}",
            "",
            "Statistics:",
            f"  Total Files: {self.total_files}",
            f"  Successful: {self.successful_files}",
            f"  Failed: {self.failed_files}",
            f"  Skipped: {self.skipped_files}",
            "",
            f"Total Time: {self.total_time_seconds:.1f} seconds",
            f"Average Time per File: {self.average_time_per_file:.2f} seconds",
        ]

        if self.total_size_before > 0:
            lines.extend([
                "",
                "Size Information:",
                f"  Total Size Before: {self._format_size(self.total_size_before)}",
                f"  Total Size After: {self._format_size(self.total_size_after)}",
                f"  Total Reduction: {self._format_size(self.total_reduction_bytes)}",
                f"  Average Reduction: {self.average_reduction_percent:.1f}%",
            ])

        if self.failed_file_details:
            lines.extend([
                "",
                "Failed Files:",
            ])
            for detail in self.failed_file_details:
                lines.append(f"  - {detail.get('file', 'Unknown')}: {detail.get('error', 'Unknown error')}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"


class BatchProcessor:
    """Coordinates batch processing operations."""

    def __init__(self):
        """Initialize batch processor."""
        self.logger = logging.getLogger(__name__)
        self._current_config: Optional[BatchConfiguration] = None
        self._is_running = False
        self._should_stop = False

    @property
    def is_running(self) -> bool:
        """Check if batch processing is running."""
        return self._is_running

    def request_stop(self) -> None:
        """Request to stop current batch processing."""
        if self._is_running:
            self._should_stop = True
            self.logger.info("Batch stop requested")

    def process_batch(self,
                     config: BatchConfiguration,
                     process_func: Callable[[List[str], str, Dict[str, Any], Optional[Callable]], ProcessingResults],
                     progress_callback: Optional[Callable[[int, int, str], None]] = None) -> BatchSummary:
        """Process a batch of files.

        Args:
            config: Batch configuration
            process_func: Function to process files (files, output_dir, settings, callback) -> ProcessingResults
            progress_callback: Callback for progress updates

        Returns:
            BatchSummary: Summary of the batch processing
        """
        self._is_running = True
        self._should_stop = False
        self._current_config = config

        summary = BatchSummary(
            name=config.name,
            processing_type=config.processing_type,
            started_at=datetime.now().isoformat(),
            total_files=len(config.files)
        )

        try:
            mode = BatchMode(config.mode)
            files_to_process = config.files.copy()
            all_results: List[ProcessingResult] = []

            # Process files
            retry_count = 0
            while files_to_process and not self._should_stop:
                # Call the processing function
                results = process_func(
                    files_to_process,
                    config.output_dir,
                    config.settings,
                    progress_callback
                )

                # Collect results
                for result in results.results:
                    if result.success:
                        all_results.append(result)
                        if result.input_file in files_to_process:
                            files_to_process.remove(result.input_file)
                    else:
                        # Handle failure
                        if mode == BatchMode.STOP_ON_FAILURE:
                            # Add the failed result and stop
                            all_results.append(result)
                            self._should_stop = True
                            break
                        else:
                            # Continue on error
                            all_results.append(result)
                            if result.input_file in files_to_process:
                                files_to_process.remove(result.input_file)

                # Check for retries
                if files_to_process and retry_count < config.max_retries:
                    retry_count += 1
                    self.logger.info(f"Retrying {len(files_to_process)} failed files (attempt {retry_count})")
                else:
                    break

            # Build summary
            summary.completed_at = datetime.now().isoformat()
            summary = self._build_summary(summary, all_results)

            if self._should_stop and files_to_process:
                summary.skipped_files = len(files_to_process)

        except Exception as e:
            self.logger.error(f"Batch processing error: {e}")
            summary.completed_at = datetime.now().isoformat()
        finally:
            self._is_running = False
            self._should_stop = False
            self._current_config = None

        return summary

    def _build_summary(self, summary: BatchSummary,
                       results: List[ProcessingResult]) -> BatchSummary:
        """Build summary from results."""
        total_time = 0.0
        total_before = 0
        total_after = 0
        reduction_percents = []

        for result in results:
            total_time += result.processing_time

            if result.success:
                summary.successful_files += 1

                if result.file_size_before:
                    total_before += result.file_size_before
                if result.file_size_after:
                    total_after += result.file_size_after

                if result.file_size_before and result.file_size_after:
                    reduction = ((result.file_size_before - result.file_size_after)
                                / result.file_size_before * 100)
                    reduction_percents.append(reduction)
            else:
                summary.failed_files += 1
                summary.failed_file_details.append({
                    'file': Path(result.input_file).name,
                    'error': result.error_message or "Unknown error"
                })

        summary.total_time_seconds = total_time
        if len(results) > 0:
            summary.average_time_per_file = total_time / len(results)

        summary.total_size_before = total_before
        summary.total_size_after = total_after
        summary.total_reduction_bytes = total_before - total_after

        if reduction_percents:
            summary.average_reduction_percent = sum(reduction_percents) / len(reduction_percents)

        return summary

    def save_configuration(self, config: BatchConfiguration, file_path: str) -> bool:
        """Save batch configuration to file.

        Args:
            config: Configuration to save
            file_path: Path to save to

        Returns:
            True if saved successfully
        """
        try:
            config.created_at = datetime.now().isoformat()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved batch configuration to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save batch configuration: {e}")
            return False

    def load_configuration(self, file_path: str) -> Optional[BatchConfiguration]:
        """Load batch configuration from file.

        Args:
            file_path: Path to load from

        Returns:
            BatchConfiguration or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            config = BatchConfiguration.from_dict(data)
            self.logger.info(f"Loaded batch configuration from {file_path}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load batch configuration: {e}")
            return None

    def save_summary(self, summary: BatchSummary, file_path: str) -> bool:
        """Save batch summary to file.

        Args:
            summary: Summary to save
            file_path: Path to save to (supports .json or .txt)

        Returns:
            True if saved successfully
        """
        try:
            path = Path(file_path)

            if path.suffix.lower() == '.json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(summary.to_report())

            self.logger.info(f"Saved batch summary to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save batch summary: {e}")
            return False
