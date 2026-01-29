import fitz  # PyMuPDF
import logging
from pathlib import Path
from typing import Tuple, Optional, Union
from ..core.exceptions import ProcessingError, ValidationError

class PDFLabeler:
    """Handles adding labels to PDF files using PyMuPDF."""
    
    def __init__(self, font_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.font_path = font_path

    def add_label(self, input_path: str, output_path: str, 
                 text: str,
                 position: str = "footer",
                 font_size: int = 10,
                 color: str = "#FF0000",
                 opacity: float = 1.0,
                 font_path: Optional[str] = None) -> bool:
        """
        Add label to all pages of a PDF.
        
        Args:
            input_path: Input PDF file
            output_path: Output PDF file
            text: Label text
            position: 'header', 'footer', 'top-left', 'top-right', 'bottom-left', 'bottom-right'
            font_size: Font size
            color: Hex color string (e.g., "#FF0000")
            opacity: Opacity (0.0-1.0)
            font_path: Path to custom font file (overrides instance default)
            
        Returns:
            bool: True if successful
            
        Raises:
            ValidationError: If input file invalid
            ProcessingError: If processing fails
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise ValidationError("Input file not found", file_path=str(input_path))
            
        try:
            doc = fitz.open(input_path)
            
            rgb_color = self._hex_to_rgb(color)
            fontfile = font_path or self.font_path
            
            for page in doc:
                rect = page.rect
                
                # Determine font settings
                insert_args = {
                    "fontsize": font_size,
                    "color": rgb_color,
                    "fill_opacity": opacity
                }
                
                # Font selection logic
                if fontfile and Path(fontfile).exists():
                    insert_args["fontfile"] = fontfile
                    insert_args["fontname"] = "custom"
                else:
                    if not text.isascii():
                        insert_args["fontname"] = "china-s" 
                    else:
                        insert_args["fontname"] = "helv"

                # Calculate position
                x, y, align = self._calculate_coordinates(rect, position, font_size)
                
                # Adjust X for alignment
                # We need text length to align properly
                try:
                    text_len = fitz.get_text_length(text, fontname=insert_args.get("fontname", "helv"), fontsize=font_size)
                except:
                    # Fallback if measurement fails
                    text_len = len(text) * font_size * 0.5
                
                if align == 1: # Center
                    x -= text_len / 2
                elif align == 2: # Right
                    x -= text_len

                # Insert text
                page.insert_text((x, y), text, **insert_args)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path)
            doc.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to label PDF: {e}")
            raise ProcessingError(f"Labeling failed: {str(e)}", file_path=str(input_path))

    def generate_preview(self, input_path: str, text: str,
                        position: str = "footer",
                        font_size: int = 10,
                        color: str = "#FF0000",
                        opacity: float = 1.0,
                        page_num: int = 0) -> bytes:
        """
        Generate a preview image of the labeled page.

        Returns:
            bytes: PNG image data
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise ValidationError("Input file not found", file_path=str(input_path))

        try:
            doc = fitz.open(input_path)
            if page_num >= len(doc):
                page_num = 0

            page = doc[page_num]
            rect = page.rect
            rgb_color = self._hex_to_rgb(color)
            fontfile = self.font_path # Use instance font for preview simplicity unless passed

            insert_args = {
                "fontsize": font_size,
                "color": rgb_color,
                "fill_opacity": opacity
            }

            if fontfile and Path(fontfile).exists():
                insert_args["fontfile"] = fontfile
                insert_args["fontname"] = "custom"
            else:
                if not text.isascii():
                    insert_args["fontname"] = "china-s"
                else:
                    insert_args["fontname"] = "helv"

            x, y, align = self._calculate_coordinates(rect, position, font_size)

            try:
                text_len = fitz.get_text_length(text, fontname=insert_args.get("fontname", "helv"), fontsize=font_size)
            except:
                text_len = len(text) * font_size * 0.5

            if align == 1: # Center
                x -= text_len / 2
            elif align == 2: # Right
                x -= text_len

            page.insert_text((x, y), text, **insert_args)

            # Render page to image
            pix = page.get_pixmap(alpha=False)
            img_data = pix.tobytes("png")
            doc.close()
            return img_data

        except Exception as e:
            self.logger.error(f"Preview generation failed: {e}")
            raise ProcessingError(f"Preview failed: {str(e)}", file_path=str(input_path))

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return (0, 0, 0)
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    def _calculate_coordinates(self, rect, position: str, font_size: int) -> Tuple[float, float, int]:
        """
        Calculate text insertion coordinates and alignment.
        
        Returns:
            Tuple[x, y, align]: x, y coords and alignment (0=left, 1=center, 2=right)
        """
        margin = 36 # 0.5 inch approx
        
        # Default center
        x = rect.width / 2
        y = rect.height / 2
        align = 1
        
        if position == "header":
            x = rect.width / 2
            y = margin + font_size
            align = 1
        elif position == "footer":
            x = rect.width / 2
            y = rect.height - margin
            align = 1
        elif position == "top-left":
            x = margin
            y = margin + font_size
            align = 0
        elif position == "top-right":
            x = rect.width - margin
            y = margin + font_size
            align = 2
        elif position == "bottom-left":
            x = margin
            y = rect.height - margin
            align = 0
        elif position == "bottom-right":
            x = rect.width - margin
            y = rect.height - margin
            align = 2
            
        return x, y, align
