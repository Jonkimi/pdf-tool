#!/usr/bin/env python3
"""
Document Processor GUI - Main Entry Point

A unified graphical interface for document processing operations including:
- Word to PDF conversion with image compression
- PDF compression using Ghostscript  
- PDF labeling with filenames

Usage:
    python main.py
"""

import sys
import os
import tkinter as tk
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from document_processor_gui import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)