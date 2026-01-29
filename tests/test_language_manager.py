import pytest
from unittest.mock import patch, mock_open
import json
from pathlib import Path
from document_processor_gui.core.language_manager import LanguageManager

class TestLanguageManager:
    
    def test_load_existing_language(self):
        manager = LanguageManager()
        assert manager.load_language("en")
        assert manager.current_language == "en"
        assert manager.get_text("menu.file") == "File"

    def test_load_missing_language(self):
        manager = LanguageManager()
        # Should fallback to English if missing
        # We assume "fr" does not exist
        result = manager.load_language("fr")
        
        # If "fr" doesn't exist, it attempts to load "en"
        # If "en" exists (which it does), it returns True (from the recursive call)
        # And the current language should be set to "en" inside the recursive call.
        
        assert result is True
        assert manager.current_language == "en"

    def test_get_text_formatting(self):
        manager = LanguageManager()
        manager.load_language("en")
        
        # We assume there is a message with formatting, e.g. "success": "Successfully processed {count} files"
        text = manager.get_text("messages.success", count=5)
        assert text == "Successfully processed 5 files"
        
    def test_get_text_missing_key(self):
        manager = LanguageManager()
        manager.load_language("en")
        
        key = "non.existent.key"
        text = manager.get_text(key)
        assert text == key

    def test_malformed_json(self):
        manager = LanguageManager()
        
        # Mock opening a file with invalid JSON
        # We need to target the specific file open in LanguageManager
        # But since we use instance methods, we can mock builtins.open
        # However, we must ensure we are mocking the correct call.
        
        with patch("builtins.open", mock_open(read_data="{invalid_json")):
            with patch.object(Path, "exists", return_value=True):
                # Using a dummy language code
                assert manager.load_language("bad_json") is False
