"""GUI components - File selection and list management widgets."""

import tkinter as tk
from tkinter import ttk, filedialog
import logging
from typing import List, Optional, Callable, Dict, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..core.language_manager import LanguageManager


class FileSelector:
    """Component for selecting files and folders."""

    def __init__(self, parent: tk.Widget,
                 language_manager: Optional["LanguageManager"] = None,
                 on_files_selected: Optional[Callable[[List[str]], None]] = None):
        """Initialize file selector.

        Args:
            parent: Parent tkinter widget
            language_manager: Language manager for translations
            on_files_selected: Callback when files are selected
        """
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        self.language_manager = language_manager
        self.on_files_selected = on_files_selected

        # Track last used directories
        self._last_input_dir = str(Path.home())
        self._last_output_dir = str(Path.home())

        # File type filters
        self.file_filters = {
            'word': [
                ("Word Documents", "*.docx *.doc *.rtf"),
                ("All Files", "*.*")
            ],
            'pdf': [
                ("PDF Documents", "*.pdf"),
                ("All Files", "*.*")
            ],
            'all': [
                ("All Files", "*.*")
            ]
        }

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def set_last_input_dir(self, directory: str) -> None:
        """Set the last used input directory."""
        if directory and Path(directory).is_dir():
            self._last_input_dir = directory

    def set_last_output_dir(self, directory: str) -> None:
        """Set the last used output directory."""
        if directory and Path(directory).is_dir():
            self._last_output_dir = directory

    def select_files(self, file_type: str = "all",
                     multiple: bool = True) -> List[str]:
        """Open file dialog to select files.

        Args:
            file_type: Type of files to filter ('word', 'pdf', 'all')
            multiple: Allow multiple file selection

        Returns:
            List of selected file paths
        """
        title = self._get_text('dialogs.select_input_files')
        filters = self.file_filters.get(file_type, self.file_filters['all'])

        if multiple:
            files = filedialog.askopenfilenames(
                parent=self.parent,
                title=title,
                initialdir=self._last_input_dir,
                filetypes=filters
            )
        else:
            file = filedialog.askopenfilename(
                parent=self.parent,
                title=title,
                initialdir=self._last_input_dir,
                filetypes=filters
            )
            files = (file,) if file else ()

        # Convert to list and update last directory
        file_list = list(files)
        if file_list:
            self._last_input_dir = str(Path(file_list[0]).parent)
            if self.on_files_selected:
                self.on_files_selected(file_list)

        return file_list

    def select_folder(self) -> Optional[str]:
        """Open folder dialog to select a folder.

        Returns:
            Selected folder path or None
        """
        title = self._get_text('dialogs.select_output_directory')

        folder = filedialog.askdirectory(
            parent=self.parent,
            title=title,
            initialdir=self._last_output_dir
        )

        if folder:
            self._last_output_dir = folder

        return folder if folder else None


class FileListWidget(ttk.Frame):
    """Widget for displaying and managing a list of files."""

    def __init__(self, parent: tk.Widget,
                 language_manager: Optional["LanguageManager"] = None,
                 on_selection_changed: Optional[Callable[[List[str]], None]] = None,
                 show_size: bool = True,
                 show_status: bool = False):
        """Initialize file list widget.

        Args:
            parent: Parent tkinter widget
            language_manager: Language manager for translations
            on_selection_changed: Callback when selection changes
            show_size: Show file size column
            show_status: Show status column
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.language_manager = language_manager
        self.on_selection_changed = on_selection_changed
        self.show_size = show_size
        self.show_status = show_status

        # Internal file list
        self._files: List[str] = []
        self._file_status: Dict[str, str] = {}

        self._setup_ui()
        self._setup_drag_drop()

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup the widget UI."""
        # Configure columns
        columns = ['filename']
        if self.show_size:
            columns.append('size')
        if self.show_status:
            columns.append('status')

        # Create treeview
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            selectmode='extended'
        )

        # Configure columns
        self.tree.heading('filename', text=self._get_text('table_headers.filename'))
        self.tree.column('filename', width=300, minwidth=150)

        if self.show_size:
            self.tree.heading('size', text=self._get_text('table_headers.size'))
            self.tree.column('size', width=80, minwidth=60)

        if self.show_status:
            self.tree.heading('status', text=self._get_text('table_headers.status'))
            self.tree.column('status', width=100, minwidth=80)

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self._on_selection_change)

        # Context menu
        self._setup_context_menu()

    def _setup_context_menu(self):
        """Setup right-click context menu."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label=self._get_text('buttons.remove_files'),
            command=self.remove_selected
        )
        self.context_menu.add_command(
            label=self._get_text('buttons.clear_list'),
            command=self.clear
        )

        self.tree.bind('<Button-3>', self._show_context_menu)
        # macOS right-click
        self.tree.bind('<Button-2>', self._show_context_menu)

    def _show_context_menu(self, event):
        """Show context menu."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _setup_drag_drop(self):
        """Setup drag and drop support."""
        # Note: tkinter doesn't have native drag-drop from OS
        # This would require platform-specific extensions like tkinterdnd2
        # For now, we'll provide methods that can be called externally
        pass

    def _on_selection_change(self, event):
        """Handle selection change."""
        if self.on_selection_changed:
            selected = self.get_selected_files()
            self.on_selection_changed(selected)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def add_files(self, files: List[str]) -> None:
        """Add files to the list.

        Args:
            files: List of file paths to add
        """
        for file_path in files:
            if file_path not in self._files:
                self._files.append(file_path)
                self._add_file_to_tree(file_path)

    def _add_file_to_tree(self, file_path: str) -> None:
        """Add a single file to the tree."""
        path = Path(file_path)
        values = [path.name]

        if self.show_size:
            try:
                size = path.stat().st_size
                values.append(self._format_size(size))
            except OSError:
                values.append("N/A")

        if self.show_status:
            status = self._file_status.get(file_path, "Pending")
            values.append(status)

        self.tree.insert('', 'end', iid=file_path, values=values)

    def remove_files(self, files: List[str]) -> None:
        """Remove files from the list.

        Args:
            files: List of file paths to remove
        """
        for file_path in files:
            if file_path in self._files:
                self._files.remove(file_path)
                self._file_status.pop(file_path, None)
                try:
                    self.tree.delete(file_path)
                except tk.TclError:
                    pass

    def remove_selected(self) -> None:
        """Remove selected files from the list."""
        selected = self.get_selected_files()
        self.remove_files(selected)

    def clear(self) -> None:
        """Clear all files from the list."""
        self._files.clear()
        self._file_status.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def get_files(self) -> List[str]:
        """Get all files in the list.

        Returns:
            List of file paths
        """
        return self._files.copy()

    def get_selected_files(self) -> List[str]:
        """Get currently selected files.

        Returns:
            List of selected file paths
        """
        return list(self.tree.selection())

    def set_file_status(self, file_path: str, status: str) -> None:
        """Set status for a file.

        Args:
            file_path: File path
            status: Status text
        """
        self._file_status[file_path] = status
        if self.show_status and self.tree.exists(file_path):
            # Update the status column
            current_values = list(self.tree.item(file_path, 'values'))
            if len(current_values) >= 3:
                current_values[2] = status
            else:
                current_values.append(status)
            self.tree.item(file_path, values=current_values)

    def update_translations(self) -> None:
        """Update UI text with current language."""
        # Update column headers
        self.tree.heading('filename', text=self._get_text('table_headers.filename'))
        if self.show_size:
            self.tree.heading('size', text=self._get_text('table_headers.size'))
        if self.show_status:
            self.tree.heading('status', text=self._get_text('table_headers.status'))

        # Update context menu
        self.context_menu.entryconfigure(0, label=self._get_text('buttons.remove_files'))
        self.context_menu.entryconfigure(1, label=self._get_text('buttons.clear_list'))

    def get_file_count(self) -> int:
        """Get the number of files in the list."""
        return len(self._files)


class OutputSelector(ttk.Frame):
    """Widget for selecting output directory."""

    def __init__(self, parent: tk.Widget,
                 language_manager: Optional["LanguageManager"] = None,
                 on_directory_changed: Optional[Callable[[str], None]] = None):
        """Initialize output selector.

        Args:
            parent: Parent tkinter widget
            language_manager: Language manager for translations
            on_directory_changed: Callback when directory changes
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.language_manager = language_manager
        self.on_directory_changed = on_directory_changed

        self._current_dir = str(Path.home())

        self._setup_ui()

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup the widget UI."""
        # Label
        self.label = ttk.Label(self, text=self._get_text('labels.output_directory'))
        self.label.grid(row=0, column=0, sticky='w', padx=(0, 5))

        # Entry for path display
        self.path_var = tk.StringVar(value=self._current_dir)
        self.path_entry = ttk.Entry(self, textvariable=self.path_var, width=50)
        self.path_entry.grid(row=0, column=1, sticky='ew', padx=5)

        # Browse button
        self.browse_button = ttk.Button(
            self,
            text=self._get_text('buttons.browse'),
            command=self._browse
        )
        self.browse_button.grid(row=0, column=2, padx=(5, 0))

        self.grid_columnconfigure(1, weight=1)

    def _browse(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(
            parent=self,
            title=self._get_text('dialogs.select_output_directory'),
            initialdir=self._current_dir
        )
        if folder:
            self.set_directory(folder)

    def set_directory(self, directory: str) -> None:
        """Set the current directory.

        Args:
            directory: Directory path
        """
        self._current_dir = directory
        self.path_var.set(directory)
        if self.on_directory_changed:
            self.on_directory_changed(directory)

    def get_directory(self) -> str:
        """Get the current directory.

        Returns:
            Current directory path
        """
        return self.path_var.get()

    def update_translations(self) -> None:
        """Update UI text with current language."""
        self.label.configure(text=self._get_text('labels.output_directory'))
        self.browse_button.configure(text=self._get_text('buttons.browse'))


class FileButtonBar(ttk.Frame):
    """Button bar for file operations."""

    def __init__(self, parent: tk.Widget,
                 language_manager: Optional["LanguageManager"] = None,
                 on_add_files: Optional[Callable[[], None]] = None,
                 on_add_folder: Optional[Callable[[], None]] = None,
                 on_remove_selected: Optional[Callable[[], None]] = None,
                 on_clear_all: Optional[Callable[[], None]] = None):
        """Initialize button bar.

        Args:
            parent: Parent tkinter widget
            language_manager: Language manager for translations
            on_add_files: Callback for add files button
            on_add_folder: Callback for add folder button
            on_remove_selected: Callback for remove selected button
            on_clear_all: Callback for clear all button
        """
        super().__init__(parent)
        self.language_manager = language_manager
        self.on_add_files = on_add_files
        self.on_add_folder = on_add_folder
        self.on_remove_selected = on_remove_selected
        self.on_clear_all = on_clear_all

        self._setup_ui()

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup the widget UI."""
        self.add_files_btn = ttk.Button(
            self,
            text=self._get_text('buttons.add_files'),
            command=self._on_add_files
        )
        self.add_files_btn.pack(side='left', padx=2)

        self.add_folder_btn = ttk.Button(
            self,
            text=self._get_text('buttons.select_folder'),
            command=self._on_add_folder
        )
        self.add_folder_btn.pack(side='left', padx=2)

        self.remove_btn = ttk.Button(
            self,
            text=self._get_text('buttons.remove_files'),
            command=self._on_remove_selected
        )
        self.remove_btn.pack(side='left', padx=2)

        self.clear_btn = ttk.Button(
            self,
            text=self._get_text('buttons.clear_list'),
            command=self._on_clear_all
        )
        self.clear_btn.pack(side='left', padx=2)

    def _on_add_files(self):
        if self.on_add_files:
            self.on_add_files()

    def _on_add_folder(self):
        if self.on_add_folder:
            self.on_add_folder()

    def _on_remove_selected(self):
        if self.on_remove_selected:
            self.on_remove_selected()

    def _on_clear_all(self):
        if self.on_clear_all:
            self.on_clear_all()

    def update_translations(self) -> None:
        """Update UI text with current language."""
        self.add_files_btn.configure(text=self._get_text('buttons.add_files'))
        self.add_folder_btn.configure(text=self._get_text('buttons.select_folder'))
        self.remove_btn.configure(text=self._get_text('buttons.remove_files'))
        self.clear_btn.configure(text=self._get_text('buttons.clear_list'))
