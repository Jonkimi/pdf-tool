import shutil
import os
from pathlib import Path
from typing import List, Optional
import logging

class FileSystemService:
    """Handles file system operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def ensure_directory(self, path: str) -> bool:
        """Ensure directory exists."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            return False

    def copy_file(self, src: str, dst: str) -> bool:
        """Copy file."""
        try:
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            self.logger.error(f"Failed to copy file {src} to {dst}: {e}")
            return False
            
    def delete_file(self, path: str) -> bool:
        """Delete file."""
        try:
            os.remove(path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete file {path}: {e}")
            return False
