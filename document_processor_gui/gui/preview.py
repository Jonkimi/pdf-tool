"""Preview panel component for displaying PDF previews."""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Callable, TYPE_CHECKING
from pathlib import Path
import io

if TYPE_CHECKING:
    from ..core.language_manager import LanguageManager

# Try to import PIL for image handling
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import fitz (PyMuPDF) for PDF rendering
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


class PreviewPanel(ttk.Frame):
    """Panel for displaying PDF and document previews."""

    def __init__(self, parent: tk.Widget,
                 language_manager: Optional["LanguageManager"] = None,
                 preview_size: int = 400,
                 on_zoom_changed: Optional[Callable[[float], None]] = None):
        """Initialize preview panel.

        Args:
            parent: Parent tkinter widget
            language_manager: Language manager for translations
            preview_size: Default preview size in pixels
            on_zoom_changed: Callback when zoom level changes
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.language_manager = language_manager
        self.preview_size = preview_size
        self.on_zoom_changed = on_zoom_changed

        # State
        self._current_file: Optional[str] = None
        self._current_page = 0
        self._total_pages = 0
        self._zoom_level = 1.0
        self._image_ref: Optional["ImageTk.PhotoImage"] = None
        self._pdf_doc: Optional["fitz.Document"] = None
        self._on_page_render: Optional[Callable[[int], Optional[bytes]]] = None

        self._setup_ui()

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup the widget UI."""
        # Preview label/canvas
        self.preview_frame = ttk.Frame(self)
        self.preview_frame.pack(fill='both', expand=True)

        # Canvas for image display with scrollbars
        self.canvas = tk.Canvas(
            self.preview_frame,
            bg='#f0f0f0',
            width=self.preview_size,
            height=self.preview_size
        )
        v_scroll = ttk.Scrollbar(self.preview_frame, orient='vertical', command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(self.preview_frame, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Layout with scrollbars
        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        # Placeholder message
        self._placeholder_id = self.canvas.create_text(
            self.preview_size // 2,
            self.preview_size // 2,
            text="No preview available",
            fill='gray'
        )

        # Control bar
        control_frame = ttk.Frame(self)
        control_frame.pack(fill='x', pady=5)

        # Navigation
        self.prev_btn = ttk.Button(control_frame, text="<", width=3, command=self._prev_page)
        self.prev_btn.pack(side='left', padx=2)

        self.page_label = ttk.Label(control_frame, text="0 / 0")
        self.page_label.pack(side='left', padx=5)

        self.next_btn = ttk.Button(control_frame, text=">", width=3, command=self._next_page)
        self.next_btn.pack(side='left', padx=2)

        # Separator
        ttk.Separator(control_frame, orient='vertical').pack(side='left', fill='y', padx=10)

        # Zoom controls
        ttk.Label(control_frame, text="Zoom:").pack(side='left', padx=2)

        self.zoom_out_btn = ttk.Button(control_frame, text="-", width=3, command=self._zoom_out)
        self.zoom_out_btn.pack(side='left', padx=2)

        self.zoom_label = ttk.Label(control_frame, text="100%", width=6)
        self.zoom_label.pack(side='left', padx=2)

        self.zoom_in_btn = ttk.Button(control_frame, text="+", width=3, command=self._zoom_in)
        self.zoom_in_btn.pack(side='left', padx=2)

        self.fit_btn = ttk.Button(control_frame, text="Fit", width=5, command=self._fit_to_window)
        self.fit_btn.pack(side='left', padx=5)

        # Initially disable controls
        self._update_controls_state(False)

        # Bind mouse wheel for scrolling
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Button-4>', self._on_mousewheel)
        self.canvas.bind('<Button-5>', self._on_mousewheel)

    def _update_controls_state(self, enabled: bool):
        """Update control buttons state."""
        state = 'normal' if enabled else 'disabled'
        self.prev_btn.configure(state=state)
        self.next_btn.configure(state=state)
        self.zoom_in_btn.configure(state=state)
        self.zoom_out_btn.configure(state=state)
        self.fit_btn.configure(state=state)

    def _on_mousewheel(self, event):
        """Handle mouse wheel for scrolling."""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, 'units')
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, 'units')

    def load_file(self, file_path: str) -> bool:
        """Load a file for preview.

        Args:
            file_path: Path to file to preview

        Returns:
            True if loaded successfully
        """
        if not HAS_FITZ:
            self._show_placeholder("PyMuPDF not available")
            return False

        path = Path(file_path)
        if not path.exists():
            self._show_placeholder("File not found")
            return False

        try:
            # Close previous document
            self._close_document()

            # Open new document
            self._pdf_doc = fitz.open(str(path))
            self._current_file = str(path)
            self._current_page = 0
            self._total_pages = len(self._pdf_doc)

            self._update_controls_state(True)
            self._render_current_page()

            return True

        except Exception as e:
            self.logger.error(f"Failed to load preview: {e}")
            self._show_placeholder(f"Cannot preview: {e}")
            return False

    def load_from_bytes(self, data: bytes, file_type: str = "png",
                        total_pages: int = 1) -> bool:
        """Load preview from image bytes.

        Args:
            data: Image data bytes
            file_type: Image format type
            total_pages: Total number of pages (for pagination controls)

        Returns:
            True if loaded successfully
        """
        if not HAS_PIL:
            self._show_placeholder("PIL not available")
            return False

        try:
            # Close any open PDF document since we're switching to bytes mode
            self._close_document()

            # Load image from bytes
            image = Image.open(io.BytesIO(data))
            self._display_image(image)

            # Set pagination state
            self._current_page = 0
            self._total_pages = total_pages
            self.page_label.configure(text=f"1 / {total_pages}")
            self._update_controls_state(total_pages > 0)

            return True

        except Exception as e:
            self.logger.error(f"Failed to load image from bytes: {e}")
            self._show_placeholder(f"Cannot display: {e}")
            return False

    def _render_current_page(self):
        """Render the current page of the loaded PDF or via callback."""
        if not HAS_PIL:
            return

        # Try callback-based rendering first (for PNG preview mode)
        if self._on_page_render:
            try:
                data = self._on_page_render(self._current_page)
                if data:
                    image = Image.open(io.BytesIO(data))
                    self._display_image(image)
                    self.page_label.configure(
                        text=f"{self._current_page + 1} / {self._total_pages}")
                    return
            except Exception as e:
                self.logger.error(f"Failed to render page via callback: {e}")

        # Fall back to PDF document rendering
        if not self._pdf_doc or not HAS_FITZ:
            return

        try:
            page = self._pdf_doc[self._current_page]

            # Calculate zoom matrix
            zoom = self._zoom_level * 2  # Base zoom for better quality
            mat = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            self._display_image(img)

            # Update page label
            self.page_label.configure(text=f"{self._current_page + 1} / {self._total_pages}")

        except Exception as e:
            self.logger.error(f"Failed to render page: {e}")
            self._show_placeholder(f"Render error: {e}")

    def _display_image(self, image: "Image.Image"):
        """Display a PIL Image on the canvas."""
        if not HAS_PIL:
            return

        # Apply zoom to the image
        width = int(image.width * self._zoom_level)
        height = int(image.height * self._zoom_level)

        # Resize if needed
        if width != image.width or height != image.height:
            image = image.resize((width, height), Image.Resampling.LANCZOS)

        # Convert to PhotoImage
        self._image_ref = ImageTk.PhotoImage(image)

        # Clear canvas
        self.canvas.delete('all')

        # Display image
        self.canvas.create_image(0, 0, anchor='nw', image=self._image_ref)

        # Update scroll region
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def _show_placeholder(self, message: str = "No preview available"):
        """Show placeholder message."""
        self.canvas.delete('all')
        self._placeholder_id = self.canvas.create_text(
            self.preview_size // 2,
            self.preview_size // 2,
            text=message,
            fill='gray',
            font=('TkDefaultFont', 10)
        )
        self.canvas.configure(scrollregion=(0, 0, self.preview_size, self.preview_size))
        self._update_controls_state(False)

    def _prev_page(self):
        """Go to previous page."""
        if self._current_page > 0:
            self._current_page -= 1
            self._render_current_page()

    def _next_page(self):
        """Go to next page."""
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._render_current_page()

    def _zoom_in(self):
        """Zoom in."""
        self._zoom_level = min(self._zoom_level * 1.25, 4.0)
        self._update_zoom()

    def _zoom_out(self):
        """Zoom out."""
        self._zoom_level = max(self._zoom_level / 1.25, 0.25)
        self._update_zoom()

    def _fit_to_window(self):
        """Fit preview to window size."""
        self._zoom_level = 1.0
        self._update_zoom()

    def _update_zoom(self):
        """Update after zoom change."""
        self.zoom_label.configure(text=f"{int(self._zoom_level * 100)}%")

        if self._pdf_doc or self._on_page_render:
            self._render_current_page()

        if self.on_zoom_changed:
            self.on_zoom_changed(self._zoom_level)

    def set_zoom(self, zoom_level: float):
        """Set zoom level.

        Args:
            zoom_level: Zoom level (1.0 = 100%)
        """
        self._zoom_level = max(0.25, min(4.0, zoom_level))
        self._update_zoom()

    def get_zoom(self) -> float:
        """Get current zoom level.

        Returns:
            Current zoom level
        """
        return self._zoom_level

    def set_page_render_callback(self, callback: Optional[Callable[[int], Optional[bytes]]]):
        """Set callback for rendering pages by page number.

        When set, pagination uses this callback instead of a loaded PDF document.

        Args:
            callback: Function that takes page_num (0-indexed) and returns PNG bytes
        """
        self._on_page_render = callback

    def clear(self):
        """Clear the preview."""
        self._close_document()
        self._show_placeholder()

    def _close_document(self):
        """Close the current document."""
        if self._pdf_doc:
            try:
                self._pdf_doc.close()
            except Exception:
                pass
            self._pdf_doc = None

        self._current_file = None
        self._current_page = 0
        self._total_pages = 0
        self._image_ref = None
        self._on_page_render = None

    def destroy(self):
        """Clean up resources when widget is destroyed."""
        self._close_document()
        super().destroy()


class BeforeAfterPreview(ttk.Frame):
    """Side-by-side before/after preview comparison."""

    def __init__(self, parent: tk.Widget,
                 language_manager: Optional["LanguageManager"] = None):
        """Initialize before/after preview.

        Args:
            parent: Parent tkinter widget
            language_manager: Language manager for translations
        """
        super().__init__(parent)
        self.language_manager = language_manager
        self.logger = logging.getLogger(__name__)

        self._setup_ui()

    def _get_text(self, key: str, **kwargs) -> str:
        """Get translated text."""
        if self.language_manager:
            return self.language_manager.get_text(key, **kwargs)
        return key

    def _setup_ui(self):
        """Setup the widget UI."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Before label
        ttk.Label(self, text="Before", font=('TkDefaultFont', 10, 'bold')).grid(
            row=0, column=0, pady=5
        )

        # After label
        ttk.Label(self, text="After", font=('TkDefaultFont', 10, 'bold')).grid(
            row=0, column=1, pady=5
        )

        # Before preview
        self.before_preview = PreviewPanel(self, preview_size=300)
        self.before_preview.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)

        # After preview
        self.after_preview = PreviewPanel(self, preview_size=300)
        self.after_preview.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)

        # Info bar
        self.info_frame = ttk.Frame(self)
        self.info_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)

        self.before_size_label = ttk.Label(self.info_frame, text="Size: -")
        self.before_size_label.pack(side='left', padx=10)

        self.after_size_label = ttk.Label(self.info_frame, text="Size: -")
        self.after_size_label.pack(side='right', padx=10)

        self.reduction_label = ttk.Label(self.info_frame, text="Reduction: -")
        self.reduction_label.pack(side='right', padx=10)

    def load_comparison(self, before_path: str, after_path: str) -> bool:
        """Load before and after files for comparison.

        Args:
            before_path: Path to original file
            after_path: Path to processed file

        Returns:
            True if both loaded successfully
        """
        before_ok = self.before_preview.load_file(before_path)
        after_ok = self.after_preview.load_file(after_path)

        # Update size info
        if before_ok:
            before_size = Path(before_path).stat().st_size
            self.before_size_label.configure(text=f"Size: {self._format_size(before_size)}")
        else:
            self.before_size_label.configure(text="Size: -")

        if after_ok:
            after_size = Path(after_path).stat().st_size
            self.after_size_label.configure(text=f"Size: {self._format_size(after_size)}")

            if before_ok:
                reduction = ((before_size - after_size) / before_size) * 100
                if reduction > 0:
                    self.reduction_label.configure(
                        text=f"Reduction: {reduction:.1f}%",
                        foreground='green'
                    )
                else:
                    self.reduction_label.configure(
                        text=f"Increase: {abs(reduction):.1f}%",
                        foreground='red'
                    )
        else:
            self.after_size_label.configure(text="Size: -")
            self.reduction_label.configure(text="Reduction: -")

        return before_ok and after_ok

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def clear(self):
        """Clear both previews."""
        self.before_preview.clear()
        self.after_preview.clear()
        self.before_size_label.configure(text="Size: -")
        self.after_size_label.configure(text="Size: -")
        self.reduction_label.configure(text="Reduction: -", foreground='')

    def destroy(self):
        """Clean up resources when widget is destroyed."""
        self.before_preview.destroy()
        self.after_preview.destroy()
        super().destroy()
