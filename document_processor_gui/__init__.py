"""
Document Processor GUI - A unified interface for document processing operations.

This package provides a graphical user interface for:
- Word to PDF conversion with image compression
- PDF compression using Ghostscript
- PDF labeling with filenames

Author: Document Processor Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Document Processor Team"

from .main import main

__all__ = ["main"]