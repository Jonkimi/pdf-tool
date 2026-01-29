"""Main window - placeholder for now."""

import tkinter as tk


class MainWindow:
    """Main application window."""
    
    def __init__(self, root: tk.Tk, app_controller, config):
        """Initialize main window.
        
        Args:
            root: Tkinter root window
            app_controller: Application controller instance
            config: Application configuration
        """
        self.root = root
        self.app_controller = app_controller
        self.config = config
    
    def on_closing(self):
        """Handle window closing event."""
        self.root.destroy()