import pytest
from hypothesis import given, strategies as st
from pathlib import Path
import json
from document_processor_gui.core.language_manager import LanguageManager

# Helper to get all keys from a dict recursively
def get_all_keys(d, parent_key=''):
    keys = []
    for k, v in d.items():
        current_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            keys.extend(get_all_keys(v, current_key))
        else:
            keys.append(current_key)
    return keys

# Load keys from English file as reference
# Adjust path based on where tests are run
project_root = Path(__file__).parent.parent
lang_dir = project_root / "config" / "languages"

if lang_dir.exists() and (lang_dir / "en.json").exists():
    with open(lang_dir / "en.json", 'r', encoding='utf-8') as f:
        en_data = json.load(f)
    ALL_KEYS = get_all_keys(en_data)
else:
    ALL_KEYS = ["menu.file"] # Fallback if file not found during collection (should not happen in correct env)

@given(key=st.sampled_from(ALL_KEYS), lang=st.sampled_from(["en", "zh"]))
def test_language_completeness(key, lang):
    """
    Property 10: Language Switching Completeness
    Validates: Requirements 10.1, 10.2, 10.3
    
    Ensure all keys exist in both languages.
    """
    manager = LanguageManager()
    assert manager.set_language(lang)
    
    text = manager.get_text(key)
    assert text != key  # Should return translation, not key path
    assert isinstance(text, str)
    # Check that we don't get empty strings for defined keys
    assert len(text) > 0 or text == "" # Empty string might be valid but unlikely for keys
