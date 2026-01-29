"""Main application module."""

import tkinter as tk
from tkinter import messagebox
import sys
import logging
from pathlib import Path

from .config import ConfigurationManager
from .core import ApplicationController, ErrorHandler, LanguageManager
from .gui import MainWindow


def setup_logging():
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting Document Processor GUI")

        # Initialize core components
        config_manager = ConfigurationManager()
        config = config_manager.load_config()
        logger.info(f"Configuration loaded, language: {config.language}")

        # Initialize language manager with config
        language_manager = LanguageManager(config_manager)

        # Initialize error handler with language manager
        error_handler = ErrorHandler(language_manager=language_manager)

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
            language_manager=language_manager
        )

        # Configure root window
        root.deiconify()  # Show window

        logger.info("Application started successfully")

        # Start the application
        root.mainloop()

        logger.info("Application closed")

    except Exception as e:
        logger.exception("Application startup failed")
        # Show error dialog if GUI initialization fails
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "启动错误 / Startup Error",
                f"应用程序启动失败 / Application startup failed:\n{str(e)}"
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()