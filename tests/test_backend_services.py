import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
import tempfile
from document_processor_gui.backend.word_converter import WordConverter
from document_processor_gui.backend.ghostscript_wrapper import GhostscriptWrapper
from document_processor_gui.backend.pdf_labeler import PDFLabeler
from document_processor_gui.core.exceptions import ProcessingError, ValidationError, DependencyError
import fitz

class TestWordConverter:
    @patch('document_processor_gui.backend.conversion_backend.WordBackend.convert')
    @patch('document_processor_gui.backend.conversion_backend.WordBackend.is_available', return_value=True)
    def test_convert_directly(self, mock_available, mock_convert):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "test.docx"
            output_file = temp_path / "test.pdf"

            # Create dummy input file
            input_file.touch()

            # Mock convert to return True
            mock_convert.return_value = True

            converter = WordConverter()
            result = converter.convert_to_pdf(str(input_file), str(output_file))

            assert result is True
            mock_convert.assert_called_once()

    def test_unsupported_format(self):
        converter = WordConverter()
        with pytest.raises(ValidationError):
            converter.convert_to_pdf("test.txt", "test.pdf")

class TestGhostscriptWrapper:
    @patch('document_processor_gui.backend.ghostscript_installer.GhostscriptInstaller.detect_ghostscript')
    def test_init_find_gs(self, mock_detect):
        mock_detect.return_value = "/usr/bin/gs"
        wrapper = GhostscriptWrapper()
        assert wrapper.gs_path == "/usr/bin/gs"
        assert wrapper.is_available()

    @patch('document_processor_gui.backend.ghostscript_installer.GhostscriptInstaller.detect_ghostscript')
    def test_init_no_gs(self, mock_detect):
        mock_detect.return_value = None
        wrapper = GhostscriptWrapper(gs_path=None)
        # If not provided, it tries to find it. If not found, it is None.
        assert wrapper.gs_path is None
        assert not wrapper.is_available()

    @patch('subprocess.run')
    def test_compress_pdf(self, mock_run):
        wrapper = GhostscriptWrapper(gs_path="/usr/bin/gs")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "input.pdf"
            output_file = temp_path / "output.pdf"
            input_file.touch()

            mock_run.return_value = MagicMock(returncode=0, stderr="")

            result = wrapper.compress_pdf(str(input_file), str(output_file))
            assert result is True
            mock_run.assert_called_once()

    @patch('document_processor_gui.backend.ghostscript_installer.GhostscriptInstaller.detect_ghostscript')
    def test_compress_pdf_missing_gs(self, mock_detect):
        mock_detect.return_value = None
        wrapper = GhostscriptWrapper()
        with pytest.raises(DependencyError):
            wrapper.compress_pdf("in.pdf", "out.pdf")

class TestPDFLabeler:
    def test_add_label(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "input.pdf"
            output_file = temp_path / "output.pdf"
            
            # Create a dummy PDF
            doc = fitz.open()
            doc.new_page()
            doc.save(input_file)
            doc.close()
            
            labeler = PDFLabeler()
            result = labeler.add_label(str(input_file), str(output_file), "Test Label")
            
            assert result is True
            assert output_file.exists()
            
            # Verify text is in PDF
            doc = fitz.open(output_file)
            text = doc[0].get_text()
            assert "Test Label" in text
            doc.close()
