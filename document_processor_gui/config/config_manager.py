"""Configuration management for the Document Processor GUI."""

import json
import os
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .exceptions import ConfigLoadError, ConfigSaveError, ConfigValidationError


@dataclass
class AppConfig:
    """Application configuration data class."""
    
    # Language and localization
    language: str = "zh"
    
    # Default directories
    default_input_dir: str = ""
    default_output_dir: str = ""
    
    # Processing settings
    compression_quality: str = "ebook"  # screen, ebook, printer, prepress
    image_compression_enabled: bool = False
    image_quality: int = 75  # 1-100
    optimize_png: bool = True
    
    # PDF labeling settings
    label_position: str = "footer"  # header, footer, top-left, top-right, bottom-left, bottom-right
    label_font_size: int = 10
    label_font_color: str = "#FF0000"
    label_transparency: float = 1.0  # 0.0-1.0
    include_path_in_label: bool = False
    
    # UI settings
    remember_window_size: bool = True
    window_width: int = 800
    window_height: int = 600
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    theme: str = "default"
    show_preview: bool = True
    preview_size: int = 200
    
    # Processing settings
    batch_size: int = 10
    max_concurrent_operations: int = 2
    
    # Advanced settings
    ghostscript_path: str = ""
    target_dpi: int = 144
    downsample_threshold: float = 1.1
    preserve_original: bool = True
    skip_ghostscript_check: bool = False
    
    def validate(self) -> bool:
        """Validate configuration values."""
        try:
            # Validate language
            if self.language not in ["zh", "en"]:
                raise ConfigValidationError(f"Invalid language: {self.language}")
            
            # Validate compression quality
            valid_qualities = ["screen", "ebook", "printer", "prepress"]
            if self.compression_quality not in valid_qualities:
                raise ConfigValidationError(f"Invalid compression quality: {self.compression_quality}")
            
            # Validate image quality
            if not (1 <= self.image_quality <= 100):
                raise ConfigValidationError(f"Image quality must be 1-100: {self.image_quality}")
            
            # Validate label position
            valid_positions = ["header", "footer", "top-left", "top-right", "bottom-left", "bottom-right"]
            if self.label_position not in valid_positions:
                raise ConfigValidationError(f"Invalid label position: {self.label_position}")
            
            # Validate font size
            if not (6 <= self.label_font_size <= 72):
                raise ConfigValidationError(f"Font size must be 6-72: {self.label_font_size}")
            
            # Validate transparency
            if not (0.0 <= self.label_transparency <= 1.0):
                raise ConfigValidationError(f"Transparency must be 0.0-1.0: {self.label_transparency}")
            
            # Validate window dimensions
            if self.window_width < 400 or self.window_height < 300:
                raise ConfigValidationError("Window size too small")
            
            # Validate batch settings
            if self.batch_size < 1:
                raise ConfigValidationError("Batch size must be at least 1")
            
            if self.max_concurrent_operations < 1:
                raise ConfigValidationError("Max concurrent operations must be at least 1")
            
            # Validate DPI
            if self.target_dpi < 72:
                raise ConfigValidationError("Target DPI must be at least 72")
            
            # Validate threshold
            if self.downsample_threshold < 1.0:
                raise ConfigValidationError("Downsample threshold must be at least 1.0")
            
            return True
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"Validation error: {str(e)}")


class ConfigurationManager:
    """Manages application configuration with JSON persistence."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Custom configuration directory. If None, uses default.
        """
        self.logger = logging.getLogger(__name__)
        
        # Set up configuration directory
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Use user's home directory for config
            home_dir = Path.home()
            self.config_dir = home_dir / ".document_processor_gui"
        
        self.config_file = self.config_dir / "config.json"
        self.default_config_file = Path(__file__).parent.parent.parent / "config" / "default_config.json"
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._config: Optional[AppConfig] = None
    
    def load_config(self) -> AppConfig:
        """Load configuration from file or create default.
        
        Returns:
            AppConfig: Loaded or default configuration
            
        Raises:
            ConfigLoadError: If configuration cannot be loaded
        """
        try:
            # Try to load existing config
            if self.config_file.exists():
                self.logger.info(f"Loading config from {self.config_file}")
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Create config object from loaded data
                config = self._dict_to_config(config_data)
                
                # Validate loaded config
                config.validate()
                
                self._config = config
                return config
            
            else:
                # Create default config
                self.logger.info("No config file found, creating default configuration")
                config = self.get_default_config()
                
                # Save default config
                self.save_config(config)
                
                self._config = config
                return config
                
        except json.JSONDecodeError as e:
            raise ConfigLoadError(f"Invalid JSON in config file: {str(e)}")
        except ConfigValidationError as e:
            self.logger.warning(f"Config validation failed: {str(e)}, using defaults")
            # Fall back to default config
            config = self.get_default_config()
            self.save_config(config)
            self._config = config
            return config
        except Exception as e:
            raise ConfigLoadError(f"Failed to load configuration: {str(e)}")
    
    def save_config(self, config: AppConfig) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration to save
            
        Raises:
            ConfigSaveError: If configuration cannot be saved
        """
        try:
            # Validate before saving
            config.validate()
            
            # Convert to dictionary
            config_dict = asdict(config)
            
            # Save to file
            self.logger.info(f"Saving config to {self.config_file}")
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            # Update cached config
            self._config = config
            
        except ConfigValidationError as e:
            raise ConfigSaveError(f"Configuration validation failed: {str(e)}")
        except Exception as e:
            raise ConfigSaveError(f"Failed to save configuration: {str(e)}")
    
    def get_default_config(self) -> AppConfig:
        """Get default configuration.
        
        Returns:
            AppConfig: Default configuration
        """
        try:
            # Try to load from default config file
            if self.default_config_file.exists():
                with open(self.default_config_file, 'r', encoding='utf-8') as f:
                    default_data = json.load(f)
                return self._dict_to_config(default_data)
            else:
                # Return hardcoded defaults
                return AppConfig()
                
        except Exception as e:
            self.logger.warning(f"Failed to load default config file: {str(e)}, using hardcoded defaults")
            return AppConfig()
    
    def reset_to_defaults(self) -> AppConfig:
        """Reset configuration to defaults.
        
        Returns:
            AppConfig: Reset configuration
        """
        config = self.get_default_config()
        self.save_config(config)
        return config
    
    def get_config(self) -> AppConfig:
        """Get current configuration.
        
        Returns:
            AppConfig: Current configuration
        """
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_config(self, **kwargs) -> AppConfig:
        """Update specific configuration values.
        
        Args:
            **kwargs: Configuration values to update
            
        Returns:
            AppConfig: Updated configuration
        """
        config = self.get_config()
        
        # Update values
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ConfigValidationError(f"Unknown configuration key: {key}")
        
        # Save updated config
        self.save_config(config)
        return config
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> AppConfig:
        """Convert dictionary to AppConfig object.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            AppConfig: Configuration object
        """
        # Get valid field names
        valid_fields = {f.name for f in fields(AppConfig)}
        
        # Filter out unknown fields
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_fields}
        
        # Create config object
        return AppConfig(**filtered_dict)