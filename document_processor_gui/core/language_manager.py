"""Language management system."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import ConfigurationManager

class LanguageManager:
    """Manages application language and translations."""
    
    def __init__(self, config_manager: Optional["ConfigurationManager"] = None):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.current_language = "zh"
        self.translations: Dict[str, Any] = {}
        
        # Determine language directory
        # Assuming run from project root or installed package
        # We can find it relative to this file
        self.lang_dir = Path(__file__).parent.parent.parent / "config" / "languages"
        
        if config_manager:
            self.current_language = config_manager.get_config().language
            
        self.load_language(self.current_language)
        
    def load_language(self, language_code: str) -> bool:
        """Load translations for specified language.
        
        Args:
            language_code: Language code (e.g., 'en', 'zh')
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            lang_file = self.lang_dir / f"{language_code}.json"
            if not lang_file.exists():
                self.logger.error(f"Language file not found: {lang_file}")
                # Fallback to English if not found and requested was not English
                if language_code != "en":
                    self.logger.info("Falling back to English")
                    return self.load_language("en")
                return False
                
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
                
            self.current_language = language_code
            self.logger.info(f"Loaded language: {language_code}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load language {language_code}: {str(e)}")
            return False
    
    def get_text(self, key_path: str, **kwargs) -> str:
        """Get translated text for key path.
        
        Args:
            key_path: Dot-separated key path (e.g., 'menu.file')
            **kwargs: Format arguments
            
        Returns:
            str: Translated text or key_path if not found
        """
        try:
            keys = key_path.split('.')
            value = self.translations
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    self.logger.warning(f"Translation key not found: {key_path}")
                    return key_path
            
            if isinstance(value, str):
                if kwargs:
                    try:
                        return value.format(**kwargs)
                    except KeyError as e:
                        self.logger.error(f"Missing format key in translation {key_path}: {e}")
                        return value
                return value
            
            return str(value)
            
        except Exception as e:
            self.logger.error(f"Error retrieving translation for {key_path}: {str(e)}")
            return key_path

    def set_language(self, language_code: str) -> bool:
        """Switch application language.
        
        Args:
            language_code: Language code to switch to
            
        Returns:
            bool: True if switched successfully
        """
        if self.load_language(language_code):
            if self.config_manager:
                self.config_manager.update_config(language=language_code)
            return True
        return False
