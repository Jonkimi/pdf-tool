"""Language manager - placeholder for now."""


class LanguageManager:
    """Manages application language and translations."""
    
    def __init__(self):
        """Initialize language manager."""
        self.current_language = "zh"
    
    def set_language(self, language: str):
        """Set the current language.
        
        Args:
            language: Language code (e.g., 'zh', 'en')
        """
        self.current_language = language