import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import tempfile
from document_processor_gui.config.config_manager import ConfigurationManager, AppConfig
from document_processor_gui.config.exceptions import ConfigLoadError, ConfigSaveError, ConfigValidationError

class TestConfigurationManager:
    
    def test_load_config_no_file(self):
        """Test loading when config file does not exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            config = manager.load_config()
            
            # Should return default config
            assert config.language == "zh"
            # Should have created the file
            assert (Path(temp_dir) / "config.json").exists()

    def test_load_config_invalid_json(self):
        """Test loading invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            with open(config_file, "w") as f:
                f.write("{invalid_json")
            
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            with pytest.raises(ConfigLoadError) as exc:
                manager.load_config()
            assert "Invalid JSON" in str(exc.value)

    def test_load_config_validation_error(self):
        """Test loading config that fails validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            # Create config with invalid value
            invalid_config = {"language": "invalid_lang"}
            with open(config_file, "w") as f:
                json.dump(invalid_config, f)
            
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            
            # Should fallback to default
            config = manager.load_config()
            assert config.language == "zh"  # Default
            
            # File should be overwritten with valid default
            with open(config_file, "r") as f:
                data = json.load(f)
            assert data["language"] == "zh"

    def test_save_config_permission_error(self):
        """Test saving config when permission denied."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ConfigurationManager(config_dir=Path(temp_dir))
            config = AppConfig()
            
            # Mock open to raise PermissionError when trying to write
            # We need to mock open specifically for the config file path
            # But simplifying by mocking builtins.open is risky as it affects other calls.
            # However, in save_config, it's the only open call.
            
            with patch("builtins.open", side_effect=PermissionError("Denied")):
                with pytest.raises(ConfigSaveError):
                    manager.save_config(config)

    def test_validation_edge_cases(self):
        """Test specific validation edge cases."""
        config = AppConfig()
        
        # Test invalid language
        config.language = "fr"
        with pytest.raises(ConfigValidationError):
            config.validate()
        config.language = "zh"  # Reset
        
        # Test invalid compression quality
        config.compression_quality = "bad"
        with pytest.raises(ConfigValidationError):
            config.validate()
        config.compression_quality = "ebook"
        
        # Test invalid image quality
        config.image_quality = 101
        with pytest.raises(ConfigValidationError):
            config.validate()
        config.image_quality = 75
        
        # Test window dimensions
        config.window_width = 100
        with pytest.raises(ConfigValidationError):
            config.validate()
