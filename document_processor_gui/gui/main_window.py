"""Main window and tab implementations for the Document Processor GUI."""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from pathlib import Path

from .components import FileSelector, FileListWidget, OutputSelector, FileButtonBar, HelpIcon
from .dialogs import ProgressDialog, ResultsDialog, ErrorDialog, SettingsDialog
from .preview import PreviewPanel

if TYPE_CHECKING:
    from ..core.application_controller import ApplicationController
    from ..core.language_manager import LanguageManager
    from ..processing.models import ProcessingResults


class BaseProcessingTab(ttk.Frame):
    """Base class for processing tabs."""

    def __init__(self, parent: tk.Widget,
                 app_controller: "ApplicationController",
                 language_manager: Optional["LanguageManager"] = None,
                 file_type: str = "all"):
        """Initialize base tab.

        Args:
            parent: Parent widget
            app_controller: Application controller
            language_manager: Language manager
            file_type: Type of files this tab handles
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.app_controller = app_controller
        self.language_manager = language_manager
        self.file_type = file_type

        self._progress_dialog: Optional[ProgressDialog] = None
        self._processing_complete = False
        self._setup_base_ui()

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_base_ui(self):
        """Setup base UI elements."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # File selector
        self.file_selector = FileSelector(
            self,
            language_manager=self.language_manager,
            on_files_selected=self._on_files_selected
        )

        # Button bar
        self.button_bar = FileButtonBar(
            self,
            language_manager=self.language_manager,
            on_add_files=self._add_files,
            on_add_folder=self._add_folder,
            on_remove_selected=self._remove_selected,
            on_clear_all=self._clear_files
        )
        self.button_bar.grid(row=0, column=0, sticky='ew', padx=10, pady=5)

        # File list
        self.file_list = FileListWidget(
            self,
            language_manager=self.language_manager,
            show_status=True
        )
        self.file_list.grid(row=1, column=0, sticky='nsew', padx=10, pady=5)

        # Output directory
        self.output_selector = OutputSelector(
            self,
            language_manager=self.language_manager
        )
        self.output_selector.grid(row=2, column=0, sticky='ew', padx=10, pady=5)

        # Process button (placed at row 5, after options frame which is at row 4 in subclasses)
        self.process_button = ttk.Button(
            self,
            text=self._get_text('buttons.start_processing'),
            command=self._start_processing
        )
        self.process_button.grid(row=5, column=0, pady=10)

    def _add_files(self):
        """Handle add files button."""
        self.file_selector.select_files(file_type=self.file_type)

    def _add_folder(self):
        """Handle add folder button - add all matching files from folder."""
        folder = self.file_selector.select_folder()
        if folder:
            extensions = self._get_extensions_for_type()
            files = []
            for ext in extensions:
                files.extend(str(f) for f in Path(folder).glob(f'*{ext}'))
            if files:
                self.file_list.add_files(files)

    def _get_extensions_for_type(self) -> List[str]:
        """Get file extensions for the file type."""
        if self.file_type == 'word':
            return ['.docx', '.doc', '.rtf']
        elif self.file_type == 'pdf':
            return ['.pdf']
        return ['.*']

    def _remove_selected(self):
        """Handle remove selected button."""
        self.file_list.remove_selected()

    def _clear_files(self):
        """Handle clear all button."""
        self.file_list.clear()

    def _on_files_selected(self, files: List[str]):
        """Handle files being selected."""
        self.file_list.add_files(files)

    def _start_processing(self):
        """Start processing - to be implemented by subclasses."""
        raise NotImplementedError

    def _show_progress_dialog(self, title: str):
        """Show progress dialog."""
        self._processing_complete = False
        root = self.winfo_toplevel()
        self._progress_dialog = ProgressDialog(
            root,
            language_manager=self.language_manager,
            title=title,
            on_cancel=self._cancel_processing
        )

    def _cancel_processing(self):
        """Cancel current processing."""
        self.app_controller.request_cancel()

    def _on_progress(self, current: int, total: int, filename: str):
        """Handle progress update - called from background thread."""
        # Schedule GUI update on main thread
        self.after(0, lambda: self._update_progress_ui(current, total, filename))

    def _update_progress_ui(self, current: int, total: int, filename: str):
        """Update progress UI - must be called from main thread."""
        if self._processing_complete:
            return
        if self._progress_dialog:
            # Set file status BEFORE updating progress dialog, because
            # ProgressDialog.update_progress() calls self.update() which
            # processes pending events and may trigger _show_completion_ui,
            # which would set statuses to "Done". If we set "Processing..."
            # after that, it would overwrite the "Done" status.
            self.file_list.set_file_status(
                self._get_file_by_name(filename) or filename,
                self._get_text('messages.status_messages.processing')
            )
            self._progress_dialog.update_progress(current, total, filename)

    def _get_file_by_name(self, filename: str) -> Optional[str]:
        """Find full path by filename."""
        for f in self.file_list.get_files():
            if Path(f).name == filename:
                return f
        return None

    def _on_completion(self, results: "ProcessingResults"):
        """Handle processing completion - called from background thread."""
        # Schedule GUI update on main thread
        self.after(0, lambda: self._show_completion_ui(results))

    def _show_completion_ui(self, results: "ProcessingResults"):
        """Show completion UI - must be called from main thread."""
        self._processing_complete = True
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        # Update file statuses for processed files
        processed_files = set()
        for result in results.results:
            status = self._get_text('messages.status_messages.done') if result.success else self._get_text('messages.status_messages.failed')
            self.file_list.set_file_status(result.input_file, status)
            processed_files.add(result.input_file)

        # Reset unprocessed files that are still showing "Processing..." back to "Pending"
        processing_text = self._get_text('messages.status_messages.processing')
        pending_text = self._get_text('messages.status_messages.pending')
        for file_path in self.file_list.get_files():
            if file_path not in processed_files:
                if self.file_list.get_file_status(file_path) == processing_text:
                    self.file_list.set_file_status(file_path, pending_text)

        # Show results dialog
        root = self.winfo_toplevel()
        ResultsDialog(
            root,
            results,
            language_manager=self.language_manager,
            title=self._get_text('messages.processing_complete')
        )

    def _on_error(self, error_msg: str):
        """Handle processing error - called from background thread."""
        # Schedule GUI update on main thread
        self.after(0, lambda: self._show_error_ui(error_msg))

    def _show_error_ui(self, error_msg: str):
        """Show error UI - must be called from main thread."""
        self._processing_complete = True
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        # Reset files that are still showing "Processing..." back to "Pending"
        processing_text = self._get_text('messages.status_messages.processing')
        pending_text = self._get_text('messages.status_messages.pending')
        for file_path in self.file_list.get_files():
            if self.file_list.get_file_status(file_path) == processing_text:
                self.file_list.set_file_status(file_path, pending_text)

        ErrorDialog(self.language_manager).show_error(
            self.winfo_toplevel(),
            error_msg
        )

    def update_translations(self):
        """Update all UI text with current language."""
        self.button_bar.update_translations()
        self.file_list.update_translations()
        self.output_selector.update_translations()
        self.process_button.configure(text=self._get_text('buttons.start_processing'))


class ConversionTab(BaseProcessingTab):
    """Tab for Word to PDF conversion."""

    def __init__(self, parent: tk.Widget,
                 app_controller: "ApplicationController",
                 language_manager: Optional["LanguageManager"] = None):
        super().__init__(parent, app_controller, language_manager, file_type='word')
        self._setup_conversion_options()

    def _setup_conversion_options(self):
        """Setup conversion-specific options."""
        # No additional options needed for Word to PDF conversion
        pass

    def _start_processing(self):
        """Start Word to PDF conversion."""
        files = self.file_list.get_files()
        if not files:
            ErrorDialog(self.language_manager).show_warning(
                self.winfo_toplevel(),
                self._get_text('messages.no_files_selected')
            )
            return

        output_dir = self.output_selector.get_directory()
        if not output_dir:
            ErrorDialog(self.language_manager).show_warning(
                self.winfo_toplevel(),
                self._get_text('messages.invalid_output_directory')
            )
            return

        # Get settings
        settings = self.app_controller.get_settings()

        # Set callbacks
        self.app_controller.set_callbacks(
            progress_callback=self._on_progress,
            completion_callback=self._on_completion,
            error_callback=self._on_error
        )

        # Show progress dialog
        self._show_progress_dialog(self._get_text('tabs.conversion'))

        # Start conversion
        self.app_controller.start_conversion(files, output_dir, settings)

    def update_translations(self):
        """Update all UI text with current language."""
        super().update_translations()


class CompressionTab(BaseProcessingTab):
    """Tab for PDF compression."""

    def __init__(self, parent: tk.Widget,
                 app_controller: "ApplicationController",
                 language_manager: Optional["LanguageManager"] = None):
        super().__init__(parent, app_controller, language_manager, file_type='pdf')
        self._setup_compression_options()

    def _setup_compression_options(self):
        """Setup compression-specific options."""
        # Options frame
        self.options_frame = ttk.LabelFrame(self, text=self._get_text('groups.compression_options'), padding=10)
        self.options_frame.grid(row=4, column=0, sticky='ew', padx=10, pady=5)

        # Compression level preset
        self.level_preset_label = ttk.Label(self.options_frame, text=self._get_text('labels.compression_level'))
        self.level_preset_label.pack(side='left', padx=5)
        self.quality_var = tk.StringVar(
            value=self.app_controller.get_settings().get('compression_level', 'screen')
        )
        quality_combo = ttk.Combobox(
            self.options_frame,
            textvariable=self.quality_var,
            values=['screen', 'ebook', 'printer', 'prepress'],
            state='readonly',
            width=15
        )
        quality_combo.pack(side='left', padx=5)
        self.level_help = HelpIcon(self.options_frame, self._get_text('tooltips.compression_level'))
        self.level_help.pack(side='left', padx=(0, 10))

        # DPI
        self.dpi_label = ttk.Label(self.options_frame, text=self._get_text('options.dpi'))
        self.dpi_label.pack(side='left', padx=(20, 5))
        self.dpi_var = tk.IntVar(
            value=self.app_controller.get_settings().get('target_dpi', 144)
        )
        ttk.Spinbox(
            self.options_frame,
            from_=72, to=600,
            textvariable=self.dpi_var,
            width=5
        ).pack(side='left')
        self.dpi_help = HelpIcon(self.options_frame, self._get_text('tooltips.target_dpi'))
        self.dpi_help.pack(side='left', padx=(0, 10))

        # Downsample threshold
        self.threshold_label = ttk.Label(self.options_frame, text=self._get_text('options.downsample_threshold'))
        self.threshold_label.pack(side='left', padx=(20, 5))
        self.threshold_var = tk.DoubleVar(
            value=self.app_controller.get_settings().get('downsample_threshold', 1.1)
        )
        ttk.Spinbox(
            self.options_frame,
            from_=1.0, to=3.0,
            increment=0.1,
            textvariable=self.threshold_var,
            width=5
        ).pack(side='left')
        self.threshold_help = HelpIcon(self.options_frame, self._get_text('tooltips.downsample_threshold'))
        self.threshold_help.pack(side='left', padx=(0, 10))

        # Image quality
        self.image_quality_label = ttk.Label(self.options_frame, text=self._get_text('options.image_quality'))
        self.image_quality_label.pack(side='left', padx=(20, 5))
        self.image_quality_var = tk.IntVar(
            value=self.app_controller.get_settings().get('image_quality', 75)
        )
        ttk.Spinbox(
            self.options_frame,
            from_=1, to=100,
            textvariable=self.image_quality_var,
            width=5
        ).pack(side='left')
        self.image_quality_help = HelpIcon(self.options_frame, self._get_text('tooltips.image_quality'))
        self.image_quality_help.pack(side='left', padx=(0, 10))

    def _start_processing(self):
        """Start PDF compression."""
        # Check Ghostscript availability before processing
        if not self.app_controller.check_and_setup_ghostscript():
            from .dialogs import GhostscriptSetupDialog
            dialog = GhostscriptSetupDialog(
                self.winfo_toplevel(),
                language_manager=self.language_manager,
                app_controller=self.app_controller
            )
            self.winfo_toplevel().wait_window(dialog)
            # Re-check after dialog closes
            if not self.app_controller.check_and_setup_ghostscript():
                return  # User skipped, abort compression

        files = self.file_list.get_files()
        if not files:
            ErrorDialog(self.language_manager).show_warning(
                self.winfo_toplevel(),
                self._get_text('messages.no_files_selected')
            )
            return

        output_dir = self.output_selector.get_directory()
        if not output_dir:
            ErrorDialog(self.language_manager).show_warning(
                self.winfo_toplevel(),
                self._get_text('messages.invalid_output_directory')
            )
            return

        # Get settings with UI overrides
        settings = self.app_controller.get_settings()
        settings['compression_level'] = self.quality_var.get()
        settings['target_dpi'] = self.dpi_var.get()
        settings['downsample_threshold'] = self.threshold_var.get()
        settings['image_quality'] = self.image_quality_var.get()

        # Set callbacks
        self.app_controller.set_callbacks(
            progress_callback=self._on_progress,
            completion_callback=self._on_completion,
            error_callback=self._on_error
        )

        # Show progress dialog
        self._show_progress_dialog(self._get_text('tabs.compression'))

        # Start compression
        self.app_controller.start_compression(files, output_dir, settings)

    def update_translations(self):
        """Update all UI text with current language."""
        super().update_translations()
        self.options_frame.configure(text=self._get_text('groups.compression_options'))
        self.level_preset_label.configure(text=self._get_text('labels.compression_level'))
        self.dpi_label.configure(text=self._get_text('options.dpi'))
        self.threshold_label.configure(text=self._get_text('options.downsample_threshold'))
        self.image_quality_label.configure(text=self._get_text('options.image_quality'))
        # Update help tooltips
        self.level_help.update_tooltip(self._get_text('tooltips.compression_level'))
        self.dpi_help.update_tooltip(self._get_text('tooltips.target_dpi'))
        self.threshold_help.update_tooltip(self._get_text('tooltips.downsample_threshold'))
        self.image_quality_help.update_tooltip(self._get_text('tooltips.image_quality'))


class LabelingTab(BaseProcessingTab):
    """Tab for PDF labeling."""

    def __init__(self, parent: tk.Widget,
                 app_controller: "ApplicationController",
                 language_manager: Optional["LanguageManager"] = None):
        super().__init__(parent, app_controller, language_manager, file_type='pdf')
        self._setup_labeling_options()

    def _setup_labeling_options(self):
        """Setup labeling-specific options."""
        # Reconfigure grid to add preview panel
        self.grid_columnconfigure(1, weight=1)

        # Options frame
        self.options_frame = ttk.LabelFrame(self, text=self._get_text('groups.label_options'), padding=10)
        self.options_frame.grid(row=4, column=0, sticky='ew', padx=10, pady=5)

        settings = self.app_controller.get_settings()

        # Position
        ttk.Label(self.options_frame, text=self._get_text('labels.label_position')).grid(
            row=0, column=0, sticky='w', padx=5, pady=2
        )
        self.position_var = tk.StringVar(value=settings.get('label_position', 'header'))
        positions = ['header', 'footer', 'top-left', 'top-right', 'bottom-left', 'bottom-right']
        ttk.Combobox(
            self.options_frame,
            textvariable=self.position_var,
            values=positions,
            state='readonly',
            width=15
        ).grid(row=0, column=1, sticky='w', padx=5, pady=2)

        # Font size
        ttk.Label(self.options_frame, text=self._get_text('labels.font_size')).grid(
            row=1, column=0, sticky='w', padx=5, pady=2
        )
        self.font_size_var = tk.IntVar(value=settings.get('label_font_size', 10))
        ttk.Spinbox(
            self.options_frame,
            from_=6, to=72,
            textvariable=self.font_size_var,
            width=5
        ).grid(row=1, column=1, sticky='w', padx=5, pady=2)

        # Font color
        ttk.Label(self.options_frame, text=self._get_text('labels.font_color')).grid(
            row=2, column=0, sticky='w', padx=5, pady=2
        )
        self.color_var = tk.StringVar(value=settings.get('label_font_color', '#FF0000'))
        color_frame = ttk.Frame(self.options_frame)
        color_frame.grid(row=2, column=1, sticky='w', padx=5, pady=2)
        ttk.Entry(color_frame, textvariable=self.color_var, width=10).pack(side='left')
        self.color_preview = tk.Label(color_frame, width=3, bg=self.color_var.get())
        self.color_preview.pack(side='left', padx=5)

        # Preview button
        ttk.Button(
            self.options_frame,
            text=self._get_text('buttons.preview'),
            command=self._show_preview
        ).grid(row=3, column=0, columnspan=2, pady=10)

        # Preview panel (on the right side)
        self.preview_frame = ttk.LabelFrame(self, text=self._get_text('groups.preview'), padding=5)
        self.preview_frame.grid(row=0, column=1, rowspan=6, sticky='nsew', padx=10, pady=5)

        self.preview_panel = PreviewPanel(self.preview_frame, preview_size=300)
        self.preview_panel.pack(fill='both', expand=True)

    def _show_preview(self):
        """Generate and show preview."""
        files = self.file_list.get_files()
        if not files:
            ErrorDialog(self.language_manager).show_warning(
                self.winfo_toplevel(),
                self._get_text('messages.no_files_selected')
            )
            return

        # Generate preview for first file
        settings = {
            'label_position': self.position_var.get(),
            'label_font_size': self.font_size_var.get(),
            'label_font_color': self.color_var.get(),
            'label_transparency': self.app_controller.get_settings().get('label_transparency', 1.0)
        }

        preview_bytes = self.app_controller.generate_label_preview(files[0], settings)
        if preview_bytes:
            self.preview_panel.load_from_bytes(preview_bytes, 'png')

    def _start_processing(self):
        """Start PDF labeling."""
        files = self.file_list.get_files()
        if not files:
            ErrorDialog(self.language_manager).show_warning(
                self.winfo_toplevel(),
                self._get_text('messages.no_files_selected')
            )
            return

        output_dir = self.output_selector.get_directory()
        if not output_dir:
            ErrorDialog(self.language_manager).show_warning(
                self.winfo_toplevel(),
                self._get_text('messages.invalid_output_directory')
            )
            return

        # Get settings with UI overrides
        settings = self.app_controller.get_settings()
        settings['label_position'] = self.position_var.get()
        settings['label_font_size'] = self.font_size_var.get()
        settings['label_font_color'] = self.color_var.get()

        # Set callbacks
        self.app_controller.set_callbacks(
            progress_callback=self._on_progress,
            completion_callback=self._on_completion,
            error_callback=self._on_error
        )

        # Show progress dialog
        self._show_progress_dialog(self._get_text('tabs.labeling'))

        # Start labeling
        self.app_controller.start_labeling(files, output_dir, settings)

    def update_translations(self):
        """Update all UI text with current language."""
        super().update_translations()
        self.options_frame.configure(text=self._get_text('groups.label_options'))
        self.preview_frame.configure(text=self._get_text('groups.preview'))


class MainWindow:
    """Main application window."""

    def __init__(self, root: tk.Tk,
                 app_controller: "ApplicationController",
                 language_manager: Optional["LanguageManager"] = None):
        """Initialize main window.

        Args:
            root: Tkinter root window
            app_controller: Application controller instance
            language_manager: Language manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.app_controller = app_controller
        self.language_manager = language_manager

        self._setup_window()
        self._setup_menu()
        self._setup_status_bar()
        self._setup_tabs()

        # Restore window position/size
        self._restore_window_geometry()

        # Handle close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Schedule Ghostscript check after window is displayed
        self.root.after(500, self._check_ghostscript_on_startup)

    def _check_ghostscript_on_startup(self):
        """Check for Ghostscript availability at startup."""
        settings = self.app_controller.get_settings()
        if settings.get('skip_ghostscript_check', False):
            return
        if not self.app_controller.check_and_setup_ghostscript():
            self._show_ghostscript_setup_dialog()

    def _show_ghostscript_setup_dialog(self):
        """Show Ghostscript setup dialog."""
        from .dialogs import GhostscriptSetupDialog
        dialog = GhostscriptSetupDialog(
            self.root,
            language_manager=self.language_manager,
            app_controller=self.app_controller
        )
        self.root.wait_window(dialog)

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_window(self):
        """Setup main window properties."""
        self.root.title(self._get_text('app_title'))
        self.root.minsize(800, 600)

        # Set window icon
        try:
            icon_path = Path(__file__).parent.parent / 'resources' / 'app_icon.png'
            if icon_path.exists():
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
        except Exception as e:
            self.logger.warning(f"Failed to load app icon: {e}")

    def _setup_menu(self):
        """Setup menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._get_text('menu.file'), menu=file_menu)
        file_menu.add_command(
            label=self._get_text('menu.settings'),
            command=self._show_settings
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=self._get_text('menu.exit'),
            command=self.on_closing
        )

        # Language menu
        lang_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._get_text('menu.language'), menu=lang_menu)
        lang_menu.add_command(label="中文", command=lambda: self._change_language('zh'))
        lang_menu.add_command(label="English", command=lambda: self._change_language('en'))

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self._get_text('menu.help'), menu=help_menu)
        help_menu.add_command(
            label=self._get_text('menu.about'),
            command=self._show_about
        )

        self.menubar = menubar

    def _setup_status_bar(self):
        """Setup top status bar with Word and Ghostscript indicators."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill='x', padx=5, pady=(5, 0))

        # Ghostscript status indicator (right side)
        self._gs_status_frame = ttk.Frame(status_frame)
        self._gs_status_frame.pack(side='right')

        self._gs_indicator = tk.Label(
            self._gs_status_frame,
            text="●",
            font=('TkDefaultFont', 12),
            cursor="hand2"
        )
        self._gs_indicator.pack(side='left')

        self._gs_label = ttk.Label(
            self._gs_status_frame,
            text="GS",
            cursor="hand2"
        )
        self._gs_label.pack(side='left', padx=(2, 0))

        # Bind click to open setup dialog
        self._gs_indicator.bind("<Button-1>", lambda e: self._on_gs_indicator_click())
        self._gs_label.bind("<Button-1>", lambda e: self._on_gs_indicator_click())

        # Word backend status indicator (left of GS)
        self._word_status_frame = ttk.Frame(status_frame)
        self._word_status_frame.pack(side='right', padx=(0, 10))

        self._word_indicator = tk.Label(
            self._word_status_frame,
            text="●",
            font=('TkDefaultFont', 12),
            cursor="hand2"
        )
        self._word_indicator.pack(side='left')

        self._word_label = ttk.Label(
            self._word_status_frame,
            text="Word",
            cursor="hand2"
        )
        self._word_label.pack(side='left', padx=(2, 0))

        # Bind click to show backend info
        self._word_indicator.bind("<Button-1>", lambda e: self._on_word_indicator_click())
        self._word_label.bind("<Button-1>", lambda e: self._on_word_indicator_click())

        # Update indicator states
        self._update_word_indicator()
        self._update_gs_indicator()

    def _on_gs_indicator_click(self):
        """Handle click on Ghostscript indicator."""
        # Get current state to pass to dialog
        gs_available = self.app_controller.check_and_setup_ghostscript()
        gs_path = None
        if gs_available:
            self.app_controller._ensure_backends_initialized()
            gs_path = self.app_controller._gs_wrapper.gs_path

        from .dialogs import GhostscriptSetupDialog
        dialog = GhostscriptSetupDialog(
            self.root,
            language_manager=self.language_manager,
            app_controller=self.app_controller,
            gs_available=gs_available,
            gs_path=gs_path
        )
        self.root.wait_window(dialog)
        self._update_gs_indicator()

    def _update_gs_indicator(self):
        """Update Ghostscript status indicator."""
        gs_available = self.app_controller.check_and_setup_ghostscript()

        if gs_available:
            self._gs_indicator.configure(foreground='green')
            # Get path from wrapper
            self.app_controller._ensure_backends_initialized()
            gs_path = self.app_controller._gs_wrapper.gs_path
            tooltip_text = gs_path
        else:
            self._gs_indicator.configure(foreground='red')
            tooltip_text = self._get_text('ghostscript.status_not_found')

        # Set tooltip
        self._set_tooltip(self._gs_status_frame, tooltip_text)

    def _on_word_indicator_click(self):
        """Handle click on Word backend indicator."""
        backend_status = self.app_controller.get_conversion_backend_status()
        active_backend = backend_status.get('active_backend', 'None')
        word_available = backend_status.get('word', {}).get('available', False)
        lo_available = backend_status.get('libreoffice', {}).get('available', False)

        # Build status message
        lines = [self._get_text('word.status_title')]
        lines.append("")
        lines.append(f"{self._get_text('word.active_backend')}: {active_backend}")
        lines.append("")
        lines.append(f"Microsoft Word: {'✓' if word_available else '✗'}")
        lines.append(f"LibreOffice: {'✓' if lo_available else '✗'}")

        from tkinter import messagebox
        messagebox.showinfo(
            self._get_text('word.status_title'),
            "\n".join(lines),
            parent=self.root
        )

    def _update_word_indicator(self):
        """Update Word backend status indicator."""
        backend_status = self.app_controller.get_conversion_backend_status()
        active_backend = backend_status.get('active_backend', 'None')

        if active_backend != 'None':
            self._word_indicator.configure(foreground='green')
            tooltip_text = f"{self._get_text('word.active_backend')}: {active_backend}"
        else:
            self._word_indicator.configure(foreground='red')
            tooltip_text = self._get_text('word.no_backend')

        # Set tooltip
        self._set_tooltip(self._word_status_frame, tooltip_text)

    def _set_tooltip(self, widget, text):
        """Set tooltip for widget."""
        # Remove existing bindings
        widget.unbind("<Enter>")
        widget.unbind("<Leave>")

        def show_tooltip(event):
            if hasattr(widget, '_tooltip') and widget._tooltip:
                return
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = ttk.Label(
                tooltip,
                text=text,
                background="#ffffe0",
                relief='solid',
                borderwidth=1,
                padding=5
            )
            label.pack()
            widget._tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(widget, '_tooltip') and widget._tooltip:
                widget._tooltip.destroy()
                widget._tooltip = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def _setup_tabs(self):
        """Setup tabbed interface."""
        # Configure notebook style to add padding inside tab content area
        style = ttk.Style()
        style.configure('TNotebook.Tab', padding=[10, 5])
        # Add tabmargins to prevent tab labels from being covered by content area shadow on macOS
        # Format: [left, top, right, bottom] - increase bottom margin to create space between tabs and content
        style.configure('TNotebook', tabmargins=[2, 5, 2, 20])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Conversion tab
        self.conversion_tab = ConversionTab(
            self.notebook,
            self.app_controller,
            self.language_manager
        )
        self.notebook.add(
            self.conversion_tab,
            text=self._get_text('tabs.conversion'),
            padding=(0, 10, 0, 0)
        )

        # Compression tab
        self.compression_tab = CompressionTab(
            self.notebook,
            self.app_controller,
            self.language_manager
        )
        self.notebook.add(
            self.compression_tab,
            text=self._get_text('tabs.compression'),
            padding=(0, 10, 0, 0)
        )

        # Labeling tab
        self.labeling_tab = LabelingTab(
            self.notebook,
            self.app_controller,
            self.language_manager
        )
        self.notebook.add(
            self.labeling_tab,
            text=self._get_text('tabs.labeling'),
            padding=(0, 10, 0, 0)
        )

    def _restore_window_geometry(self):
        """Restore saved window geometry."""
        settings = self.app_controller.get_settings()
        width = settings.get('window_width', 800)
        height = settings.get('window_height', 600)
        x = settings.get('window_x')
        y = settings.get('window_y')

        if x is not None and y is not None:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.root.geometry(f"{width}x{height}")

    def _save_window_geometry(self):
        """Save current window geometry."""
        try:
            geometry = self.root.geometry()
            # Parse geometry string: WxH+X+Y
            size, pos = geometry.split('+', 1)
            width, height = map(int, size.split('x'))
            x, y = map(int, pos.split('+'))

            self.app_controller.update_settings(
                window_width=width,
                window_height=height,
                window_x=x,
                window_y=y
            )
        except Exception as e:
            self.logger.warning(f"Failed to save window geometry: {e}")

    def _show_settings(self):
        """Show settings dialog."""
        settings = self.app_controller.get_settings()

        def on_save(new_settings):
            for key, value in new_settings.items():
                self.app_controller.update_settings(**{key: value})
            # Handle language change
            if new_settings.get('language') != settings.get('language'):
                self._change_language(new_settings['language'])

        def on_reset():
            self.app_controller.reset_settings()
            return self.app_controller.get_settings()

        SettingsDialog(
            self.root,
            settings,
            language_manager=self.language_manager,
            on_save=on_save,
            on_reset=on_reset
        )

    def _change_language(self, language_code: str):
        """Change application language."""
        self.app_controller.set_language(language_code)
        self._update_all_translations()

    def _update_all_translations(self):
        """Update all UI text after language change."""
        # Update window title
        self.root.title(self._get_text('app_title'))

        # Update tab titles
        self.notebook.tab(0, text=self._get_text('tabs.conversion'))
        self.notebook.tab(1, text=self._get_text('tabs.compression'))
        self.notebook.tab(2, text=self._get_text('tabs.labeling'))

        # Update tabs
        self.conversion_tab.update_translations()
        self.compression_tab.update_translations()
        self.labeling_tab.update_translations()

        # Recreate menu (simplest way to update)
        self._setup_menu()

    def _show_about(self):
        """Show about dialog."""
        from tkinter import messagebox
        messagebox.showinfo(
            self._get_text('menu.about'),
            "Document Processor GUI\nVersion 1.0\n\nA unified tool for document processing.",
            parent=self.root
        )

    def on_closing(self):
        """Handle window closing event."""
        # Check if processing is in progress
        if self.app_controller.is_processing:
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Confirm Exit",
                "Processing is in progress. Are you sure you want to exit?",
                parent=self.root
            ):
                return

        # Save window geometry
        self._save_window_geometry()

        # Destroy window
        self.root.destroy()
