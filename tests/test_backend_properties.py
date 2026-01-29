import pytest
from hypothesis import given, strategies as st
from pathlib import Path
from document_processor_gui.backend.word_converter import WordConverter

@given(st.text())
def test_word_converter_format_support(filename):
    """
    Property 5: File Format Support
    Validates: Requirements 5.4
    
    Converter should identify supported formats correctly.
    """
    converter = WordConverter()
    is_supported = converter.is_supported_format(filename)
    
    suffix = Path(filename).suffix.lower()
    if suffix in ['.docx', '.doc']:
        assert is_supported
    else:
        assert not is_supported
