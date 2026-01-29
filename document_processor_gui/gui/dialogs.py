"""Dialog components for the Document Processor GUI."""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Callable, List, Dict, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..core.language_manager import LanguageManager
    from ..processing.models import ProcessingResults


class ProgressDialog(tk.Toplevel):
    """Dialog showing processing progress."""

    def __init__(self, parent: tk.Widget,
                 language_manager: Optional["LanguageManager"] = None,
                 title: str = "Processing",
                 on_cancel: Optional[Callable[[], None]] = None):
        """Initialize progress dialog.

        Args:
            parent: Parent window
            language_manager: Language manager for translations
            title: Dialog title
            on_cancel: Callback when cancel is requested
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.language_manager = language_manager
        self.on_cancel = on_cancel
        self._cancelled = False

        self.title(title)
        self.transient(parent)
        self.grab_set()

        # Prevent closing via window manager
        self.protocol("WM_DELETE_WINDOW", self._request_cancel)

        self._setup_ui()
        self._center_on_parent(parent)

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup dialog UI."""
        self.resizable(False, False)

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Current file label
        self.current_file_label = ttk.Label(
            main_frame,
            text=self._get_text('labels.current_file') + " -"
        )
        self.current_file_label.pack(anchor='w', pady=(0, 5))

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(fill='x', pady=5)

        # Progress text
        self.progress_text = ttk.Label(main_frame, text="0 / 0")
        self.progress_text.pack(pady=5)

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text=self._get_text('labels.status') + " " + self._get_text('messages.processing_complete').replace('完成', '中...')
        )
        self.status_label.pack(pady=5)

        # Cancel button
        self.cancel_button = ttk.Button(
            main_frame,
            text=self._get_text('buttons.cancel'),
            command=self._request_cancel
        )
        self.cancel_button.pack(pady=(10, 0))

    def _center_on_parent(self, parent: tk.Widget):
        """Center dialog on parent window."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        self.geometry(f"+{x}+{y}")

    def _request_cancel(self):
        """Handle cancel request."""
        if not self._cancelled:
            self._cancelled = True
            self.cancel_button.configure(state='disabled')
            self.status_label.configure(text=self._get_text('messages.processing_cancelled'))
            if self.on_cancel:
                self.on_cancel()

    def update_progress(self, current: int, total: int, filename: str = "") -> None:
        """Update progress display.

        Args:
            current: Current file number
            total: Total file count
            filename: Current filename
        """
        if total > 0:
            percentage = (current / total) * 100
            self.progress_var.set(percentage)

        self.progress_text.configure(text=f"{current} / {total}")

        if filename:
            self.current_file_label.configure(
                text=f"{self._get_text('labels.current_file')} {filename}"
            )

        self.update()

    def set_status(self, status: str) -> None:
        """Set status text.

        Args:
            status: Status message
        """
        self.status_label.configure(text=status)
        self.update()

    def complete(self) -> None:
        """Mark processing as complete."""
        self.progress_var.set(100)
        self.cancel_button.configure(
            text=self._get_text('buttons.ok'),
            command=self.close
        )
        self.status_label.configure(text=self._get_text('messages.processing_complete'))

    def close(self) -> None:
        """Close the dialog."""
        self.grab_release()
        self.destroy()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancel was requested."""
        return self._cancelled


class ResultsDialog(tk.Toplevel):
    """Dialog showing processing results summary."""

    def __init__(self, parent: tk.Widget,
                 results: "ProcessingResults",
                 language_manager: Optional["LanguageManager"] = None,
                 title: str = "Results"):
        """Initialize results dialog.

        Args:
            parent: Parent window
            results: Processing results
            language_manager: Language manager for translations
            title: Dialog title
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.language_manager = language_manager
        self.results = results

        self.title(title)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._center_on_parent(parent)

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup dialog UI."""
        self.resizable(True, True)
        self.minsize(400, 300)

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill='both', expand=True)

        # Summary section
        summary_frame = ttk.LabelFrame(main_frame, text="Summary", padding=10)
        summary_frame.pack(fill='x', pady=(0, 10))

        # Statistics
        stats = [
            (self._get_text('labels.files_processed'), str(self.results.total_files)),
            ("Successful", str(self.results.successful_files)),
            ("Failed", str(self.results.failed_files)),
            ("Total Time", f"{self.results.total_processing_time:.1f}s")
        ]

        for i, (label, value) in enumerate(stats):
            ttk.Label(summary_frame, text=f"{label}:").grid(row=i, column=0, sticky='w', padx=5)
            ttk.Label(summary_frame, text=value).grid(row=i, column=1, sticky='w', padx=5)

        # Determine overall status message
        if self.results.failed_files == 0:
            status_text = self._get_text('messages.success', count=self.results.successful_files)
            status_color = "green"
        elif self.results.successful_files == 0:
            status_text = self._get_text('messages.all_failed')
            status_color = "red"
        else:
            status_text = self._get_text(
                'messages.partial_success',
                success=self.results.successful_files,
                failed=self.results.failed_files
            )
            status_color = "orange"

        status_label = ttk.Label(summary_frame, text=status_text, foreground=status_color)
        status_label.grid(row=len(stats), column=0, columnspan=2, pady=(10, 0))

        # Details section (if there are failures)
        if self.results.failed_files > 0:
            details_frame = ttk.LabelFrame(main_frame, text="Failed Files", padding=10)
            details_frame.pack(fill='both', expand=True, pady=(0, 10))

            # Treeview for failed files
            columns = ('filename', 'error')
            tree = ttk.Treeview(details_frame, columns=columns, show='headings', height=6)
            tree.heading('filename', text='File')
            tree.heading('error', text='Error')
            tree.column('filename', width=200)
            tree.column('error', width=300)

            scrollbar = ttk.Scrollbar(details_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # Populate failed files
            for result in self.results.get_failed_files():
                filename = Path(result.input_file).name
                error = result.error_message or "Unknown error"
                tree.insert('', 'end', values=(filename, error))

        # OK button
        ok_button = ttk.Button(main_frame, text=self._get_text('buttons.ok'), command=self.close)
        ok_button.pack(pady=(10, 0))

    def _center_on_parent(self, parent: tk.Widget):
        """Center dialog on parent window."""
        self.update_idletasks()
        width = max(self.winfo_width(), 450)
        height = max(self.winfo_height(), 350)
        self.geometry(f"{width}x{height}")

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def close(self) -> None:
        """Close the dialog."""
        self.grab_release()
        self.destroy()


class ErrorDialog:
    """Utility class for showing error dialogs."""

    def __init__(self, language_manager: Optional["LanguageManager"] = None):
        """Initialize error dialog utility.

        Args:
            language_manager: Language manager for translations
        """
        self.language_manager = language_manager

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def show_error(self, parent: tk.Widget, message: str,
                   title: Optional[str] = None) -> None:
        """Show error message dialog.

        Args:
            parent: Parent window
            message: Error message
            title: Dialog title (optional)
        """
        if title is None:
            title = self._get_text('dialogs.error')
        messagebox.showerror(title, message, parent=parent)

    def show_warning(self, parent: tk.Widget, message: str,
                     title: Optional[str] = None) -> None:
        """Show warning message dialog.

        Args:
            parent: Parent window
            message: Warning message
            title: Dialog title (optional)
        """
        if title is None:
            title = self._get_text('dialogs.warning')
        messagebox.showwarning(title, message, parent=parent)

    def show_info(self, parent: tk.Widget, message: str,
                  title: Optional[str] = None) -> None:
        """Show info message dialog.

        Args:
            parent: Parent window
            message: Info message
            title: Dialog title (optional)
        """
        if title is None:
            title = self._get_text('dialogs.information')
        messagebox.showinfo(title, message, parent=parent)

    def ask_confirmation(self, parent: tk.Widget, message: str,
                         title: Optional[str] = None) -> bool:
        """Show confirmation dialog.

        Args:
            parent: Parent window
            message: Confirmation message
            title: Dialog title (optional)

        Returns:
            True if user confirmed, False otherwise
        """
        if title is None:
            title = self._get_text('dialogs.confirmation')
        return messagebox.askyesno(title, message, parent=parent)


class SettingsDialog(tk.Toplevel):
    """Dialog for editing application settings."""

    def __init__(self, parent: tk.Widget,
                 settings: Dict[str, Any],
                 language_manager: Optional["LanguageManager"] = None,
                 on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_reset: Optional[Callable[[], Dict[str, Any]]] = None):
        """Initialize settings dialog.

        Args:
            parent: Parent window
            settings: Current settings dictionary
            language_manager: Language manager for translations
            on_save: Callback when settings are saved
            on_reset: Callback to get default settings
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.language_manager = language_manager
        self.settings = settings.copy()
        self.on_save = on_save
        self.on_reset = on_reset

        self.title(self._get_text('settings.title'))
        self.transient(parent)
        self.grab_set()

        self._vars: Dict[str, tk.Variable] = {}
        self._setup_ui()
        self._center_on_parent(parent)
        self._load_values()

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup dialog UI."""
        self.resizable(True, True)
        self.minsize(500, 400)

        # Main container
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill='both', expand=True)

        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True, pady=(0, 10))

        # General settings tab
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text=self._get_text('settings.general'))
        self._setup_general_tab(general_frame)

        # Processing settings tab
        processing_frame = ttk.Frame(notebook, padding=10)
        notebook.add(processing_frame, text=self._get_text('settings.processing'))
        self._setup_processing_tab(processing_frame)

        # Labeling settings tab
        labeling_frame = ttk.Frame(notebook, padding=10)
        notebook.add(labeling_frame, text=self._get_text('settings.labeling_settings'))
        self._setup_labeling_tab(labeling_frame)

        # Advanced settings tab
        advanced_frame = ttk.Frame(notebook, padding=10)
        notebook.add(advanced_frame, text=self._get_text('settings.advanced'))
        self._setup_advanced_tab(advanced_frame)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')

        ttk.Button(
            button_frame,
            text=self._get_text('buttons.reset'),
            command=self._reset_to_defaults
        ).pack(side='left')

        ttk.Button(
            button_frame,
            text=self._get_text('buttons.cancel'),
            command=self.close
        ).pack(side='right', padx=(5, 0))

        ttk.Button(
            button_frame,
            text=self._get_text('buttons.ok'),
            command=self._save_and_close
        ).pack(side='right')

    def _setup_general_tab(self, parent: ttk.Frame):
        """Setup general settings tab."""
        row = 0

        # Language selection
        ttk.Label(parent, text=self._get_text('settings.language_selection')).grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['language'] = tk.StringVar()
        lang_combo = ttk.Combobox(
            parent,
            textvariable=self._vars['language'],
            values=['zh', 'en'],
            state='readonly',
            width=20
        )
        lang_combo.grid(row=row, column=1, sticky='w', pady=5, padx=5)
        row += 1

        # Default input directory
        ttk.Label(parent, text="Default Input Directory:").grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['default_input_dir'] = tk.StringVar()
        dir_frame = ttk.Frame(parent)
        dir_frame.grid(row=row, column=1, sticky='ew', pady=5, padx=5)
        ttk.Entry(dir_frame, textvariable=self._vars['default_input_dir'], width=30).pack(side='left', fill='x', expand=True)
        ttk.Button(
            dir_frame, text="...",
            command=lambda: self._browse_directory('default_input_dir'),
            width=3
        ).pack(side='right', padx=(5, 0))
        row += 1

        # Default output directory
        ttk.Label(parent, text="Default Output Directory:").grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['default_output_dir'] = tk.StringVar()
        dir_frame2 = ttk.Frame(parent)
        dir_frame2.grid(row=row, column=1, sticky='ew', pady=5, padx=5)
        ttk.Entry(dir_frame2, textvariable=self._vars['default_output_dir'], width=30).pack(side='left', fill='x', expand=True)
        ttk.Button(
            dir_frame2, text="...",
            command=lambda: self._browse_directory('default_output_dir'),
            width=3
        ).pack(side='right', padx=(5, 0))

        parent.grid_columnconfigure(1, weight=1)

    def _setup_processing_tab(self, parent: ttk.Frame):
        """Setup processing settings tab."""
        row = 0

        # Compression quality
        ttk.Label(parent, text=self._get_text('labels.compression_quality')).grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['compression_quality'] = tk.StringVar()
        quality_combo = ttk.Combobox(
            parent,
            textvariable=self._vars['compression_quality'],
            values=['screen', 'ebook', 'printer', 'prepress'],
            state='readonly',
            width=20
        )
        quality_combo.grid(row=row, column=1, sticky='w', pady=5, padx=5)
        row += 1

        # Image compression
        self._vars['image_compression_enabled'] = tk.BooleanVar()
        ttk.Checkbutton(
            parent,
            text=self._get_text('labels.image_compression'),
            variable=self._vars['image_compression_enabled']
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=5)
        row += 1

        # Image quality
        ttk.Label(parent, text="Image Quality (1-100):").grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['image_quality'] = tk.IntVar()
        quality_spin = ttk.Spinbox(
            parent,
            from_=1, to=100,
            textvariable=self._vars['image_quality'],
            width=10
        )
        quality_spin.grid(row=row, column=1, sticky='w', pady=5, padx=5)
        row += 1

        # Max concurrent operations
        ttk.Label(parent, text="Max Concurrent Operations:").grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['max_concurrent_operations'] = tk.IntVar()
        ttk.Spinbox(
            parent,
            from_=1, to=8,
            textvariable=self._vars['max_concurrent_operations'],
            width=10
        ).grid(row=row, column=1, sticky='w', pady=5, padx=5)

        parent.grid_columnconfigure(1, weight=1)

    def _setup_labeling_tab(self, parent: ttk.Frame):
        """Setup labeling settings tab."""
        row = 0

        # Label position
        ttk.Label(parent, text=self._get_text('labels.label_position')).grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['label_position'] = tk.StringVar()
        positions = ['header', 'footer', 'top-left', 'top-right', 'bottom-left', 'bottom-right']
        pos_combo = ttk.Combobox(
            parent,
            textvariable=self._vars['label_position'],
            values=positions,
            state='readonly',
            width=20
        )
        pos_combo.grid(row=row, column=1, sticky='w', pady=5, padx=5)
        row += 1

        # Font size
        ttk.Label(parent, text=self._get_text('labels.font_size')).grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['label_font_size'] = tk.IntVar()
        ttk.Spinbox(
            parent,
            from_=6, to=72,
            textvariable=self._vars['label_font_size'],
            width=10
        ).grid(row=row, column=1, sticky='w', pady=5, padx=5)
        row += 1

        # Font color
        ttk.Label(parent, text=self._get_text('labels.font_color')).grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['label_font_color'] = tk.StringVar()
        color_frame = ttk.Frame(parent)
        color_frame.grid(row=row, column=1, sticky='w', pady=5, padx=5)
        ttk.Entry(color_frame, textvariable=self._vars['label_font_color'], width=10).pack(side='left')
        self.color_preview = tk.Label(color_frame, width=3, background='#FF0000')
        self.color_preview.pack(side='left', padx=5)
        ttk.Button(color_frame, text="Pick", command=self._pick_color, width=5).pack(side='left')
        row += 1

        # Transparency
        ttk.Label(parent, text="Transparency:").grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['label_transparency'] = tk.DoubleVar()
        ttk.Scale(
            parent,
            from_=0.0, to=1.0,
            variable=self._vars['label_transparency'],
            orient='horizontal'
        ).grid(row=row, column=1, sticky='ew', pady=5, padx=5)
        row += 1

        # Include path in label
        self._vars['include_path_in_label'] = tk.BooleanVar()
        ttk.Checkbutton(
            parent,
            text="Include full path in label",
            variable=self._vars['include_path_in_label']
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=5)

        parent.grid_columnconfigure(1, weight=1)

    def _setup_advanced_tab(self, parent: ttk.Frame):
        """Setup advanced settings tab."""
        row = 0

        # Ghostscript path
        ttk.Label(parent, text="Ghostscript Path:").grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['ghostscript_path'] = tk.StringVar()
        gs_frame = ttk.Frame(parent)
        gs_frame.grid(row=row, column=1, sticky='ew', pady=5, padx=5)
        ttk.Entry(gs_frame, textvariable=self._vars['ghostscript_path'], width=30).pack(side='left', fill='x', expand=True)
        ttk.Button(
            gs_frame, text="...",
            command=lambda: self._browse_file('ghostscript_path'),
            width=3
        ).pack(side='right', padx=(5, 0))
        row += 1

        # Target DPI
        ttk.Label(parent, text="Target DPI:").grid(
            row=row, column=0, sticky='w', pady=5
        )
        self._vars['target_dpi'] = tk.IntVar()
        ttk.Spinbox(
            parent,
            from_=72, to=600,
            textvariable=self._vars['target_dpi'],
            width=10
        ).grid(row=row, column=1, sticky='w', pady=5, padx=5)
        row += 1

        # Preserve original
        self._vars['preserve_original'] = tk.BooleanVar()
        ttk.Checkbutton(
            parent,
            text="Preserve original files",
            variable=self._vars['preserve_original']
        ).grid(row=row, column=0, columnspan=2, sticky='w', pady=5)

        parent.grid_columnconfigure(1, weight=1)

    def _browse_directory(self, var_name: str):
        """Browse for directory."""
        from tkinter import filedialog
        directory = filedialog.askdirectory(parent=self)
        if directory:
            self._vars[var_name].set(directory)

    def _browse_file(self, var_name: str):
        """Browse for file."""
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(parent=self)
        if filepath:
            self._vars[var_name].set(filepath)

    def _pick_color(self):
        """Open color picker."""
        from tkinter import colorchooser
        color = colorchooser.askcolor(
            color=self._vars['label_font_color'].get(),
            parent=self
        )
        if color[1]:
            self._vars['label_font_color'].set(color[1].upper())
            self.color_preview.configure(background=color[1])

    def _load_values(self):
        """Load current settings into UI."""
        for key, var in self._vars.items():
            if key in self.settings:
                var.set(self.settings[key])

        # Update color preview
        try:
            color = self._vars['label_font_color'].get()
            if color:
                self.color_preview.configure(background=color)
        except Exception:
            pass

    def _save_and_close(self):
        """Save settings and close dialog."""
        # Collect values from UI
        new_settings = {}
        for key, var in self._vars.items():
            new_settings[key] = var.get()

        if self.on_save:
            self.on_save(new_settings)

        self.close()

    def _reset_to_defaults(self):
        """Reset settings to defaults."""
        if self.on_reset:
            default_settings = self.on_reset()
            self.settings = default_settings
            self._load_values()

    def _center_on_parent(self, parent: tk.Widget):
        """Center dialog on parent window."""
        self.update_idletasks()
        width = 550
        height = 450
        self.geometry(f"{width}x{height}")

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def close(self) -> None:
        """Close the dialog."""
        self.grab_release()
        self.destroy()
