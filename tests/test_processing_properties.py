import pytest
from hypothesis import given, strategies as st
from unittest.mock import MagicMock, call, ANY
from pathlib import Path
import tempfile
from document_processor_gui.processing.conversion_engine import ConversionEngine
from document_processor_gui.processing.compression_engine import CompressionEngine
from document_processor_gui.processing.models import ProcessingResult
from document_processor_gui.backend.word_converter import WordConverter
from document_processor_gui.backend.ghostscript_wrapper import GhostscriptWrapper

# Strategy for list of filenames
# Use simple alphanumeric names to avoid OS filesystem issues during testing
files_strategy = st.lists(st.from_regex(r"^[a-zA-Z0-9_-]+$", fullmatch=True).map(lambda x: f"{x}.docx"), min_size=1, max_size=10)

@given(files=files_strategy)
def test_batch_processing_progress(files):
    """
    Property 3: Batch Processing with Progress
    Validates: Requirements 3.1, 3.2, 3.3, 9.1, 9.3
    """
    mock_converter = MagicMock(spec=WordConverter)
    mock_converter.convert_to_pdf.return_value = True
    
    engine = ConversionEngine(mock_converter)
    progress_callback = MagicMock()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create dummy files
        input_files = []
        for f in files:
            p = Path(temp_dir) / f
            p.touch()
            input_files.append(str(p))
            
        results = engine.convert_files(
            input_files, 
            temp_dir, 
            {}, 
            progress_callback
        )
        
        assert results.total_files == len(files)
        assert results.successful_files == len(files)
        assert progress_callback.call_count == len(files)
        
        # Check callback args
        # Last call should have current=len(files), total=len(files)
        progress_callback.assert_called_with(len(files), len(files), ANY)

@given(files=files_strategy)
def test_batch_error_handling_independence(files):
    """
    Property 4: Batch Error Handling Independence
    Validates: Requirements 5.3, 5.5, 9.2
    """
    # Make every second file fail
    mock_converter = MagicMock(spec=WordConverter)
    
    def side_effect(inp, out, **kwargs):
        if "fail" in inp:
            return False
        return True
    
    mock_converter.convert_to_pdf.side_effect = side_effect
    
    engine = ConversionEngine(mock_converter)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        input_files = []
        for i, f in enumerate(files):
            # Create distinct names for fail/ok
            name = f"fail_{i}.docx" if i % 2 == 0 else f"ok_{i}.docx"
            p = Path(temp_dir) / name
            p.touch()
            input_files.append(str(p))
            
        results = engine.convert_files(input_files, temp_dir, {})
        
        # Expect failures
        expected_failures = len([f for f in input_files if "fail" in f])
        assert results.failed_files == expected_failures
        assert results.successful_files == len(files) - expected_failures

# Property 7: File Preservation and Naming
@given(st.from_regex(r"^[a-zA-Z0-9_-]+$", fullmatch=True))
def test_file_preservation_and_naming(filename):
    """
    Property 7: File Preservation and Naming
    Validates: Requirements 6.4, 7.5
    """
    mock_gs = MagicMock(spec=GhostscriptWrapper)
    mock_gs.compress_pdf.return_value = True
    
    engine = CompressionEngine(mock_gs)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        input_name = f"{filename}.pdf"
        p = Path(temp_dir) / input_name
        p.touch()
        
        output_dir = Path(temp_dir) / "output"
        
        # Settings for compression
        settings = {}
        
        engine.compress_files([str(p)], str(output_dir), settings)
        
        # Input file should still exist (preserved)
        assert p.exists()
        
        # Verify call arguments
        mock_gs.compress_pdf.assert_called()
        args = mock_gs.compress_pdf.call_args[0]
        # args[0] is input, args[1] is output
        assert args[0] == str(p)
        assert Path(args[1]).name == input_name
        assert Path(args[1]).parent == output_dir