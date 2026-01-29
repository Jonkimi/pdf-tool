"""Main application module."""

import tkinter as tk
from tkinter import messagebox
import sys
from pathlib import Path

from .config import ConfigurationManager
from .core import ApplicationController, ErrorHandler, LanguageManager
from .gui import MainWindow


def main():
    """Main application entry point."""
    try:
        # Initialize core components
        config_manager = ConfigurationManager()
        error_handler = ErrorHandler()
        language_manager = LanguageManager()
        
        # Load configuration
        config = config_manager.load_config()
        
        # Set up language
        language_manager.set_language(config.language)
        
        # Create main application
        root = tk.Tk()
        root.withdraw()  # Hide root window initially
        
        # Initialize application controller
        app_controller = ApplicationController(
            config_manager=config_manager,
            error_handler=error_handler,
            language_manager=language_manager
        )
        
        # Create and show main window
        main_window = MainWindow(
            root=root,
            app_controller=app_controller,
            config=config
        )
        
        # Configure root window
        root.deiconify()  # Show window
        root.protocol("WM_DELETE_WINDOW", main_window.on_closing)
        
        # Start the application
        root.mainloop()
        
    except Exception as e:
        # Show error dialog if GUI initialization fails
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "启动错误 / Startup Error",
            f"应用程序启动失败 / Application startup failed:\n{str(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()