import pytest
from hypothesis import given, strategies as st
from pathlib import Path
import tempfile
from document_processor_gui.config.config_manager import ConfigurationManager, AppConfig

# Strategy for generating valid AppConfig objects
@st.composite
def app_config_strategy(draw):
    return AppConfig(
        language=draw(st.sampled_from(["zh", "en"])),
        default_input_dir=draw(st.text()),
        default_output_dir=draw(st.text()),
        compression_quality=draw(st.sampled_from(["screen", "ebook", "printer", "prepress"])),
        image_compression_enabled=draw(st.booleans()),
        image_quality=draw(st.integers(min_value=1, max_value=100)),
        optimize_png=draw(st.booleans()),
        label_position=draw(st.sampled_from(["header", "footer", "top-left", "top-right", "bottom-left", "bottom-right"])),
        label_font_size=draw(st.integers(min_value=6, max_value=72)),
        label_font_color=draw(st.text(min_size=1)),
        label_transparency=draw(st.floats(min_value=0.0, max_value=1.0)),
        include_path_in_label=draw(st.booleans()),
        remember_window_size=draw(st.booleans()),
        window_width=draw(st.integers(min_value=400, max_value=2000)),
        window_height=draw(st.integers(min_value=300, max_value=2000)),
        window_x=draw(st.one_of(st.none(), st.integers(min_value=0, max_value=2000))),
        window_y=draw(st.one_of(st.none(), st.integers(min_value=0, max_value=2000))),
        theme=draw(st.text()),
        show_preview=draw(st.booleans()),
        preview_size=draw(st.integers(min_value=100, max_value=500)),
        batch_size=draw(st.integers(min_value=1, max_value=100)),
        max_concurrent_operations=draw(st.integers(min_value=1, max_value=10)),
        ghostscript_path=draw(st.text()),
        target_dpi=draw(st.integers(min_value=72, max_value=600)),
        downsample_threshold=draw(st.floats(min_value=1.0, max_value=5.0)),
        preserve_original=draw(st.booleans())
    )

@given(config=app_config_strategy())
def test_config_persistence(config):
    """
    Property 2: Settings Persistence
    Validates: Requirements 2.5, 4.2, 4.4, 10.4
    
    For any configuration change (directories, language, compression settings, label formatting),
    when the application is restarted, the modified settings should be preserved and applied.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize manager with temp directory
        manager = ConfigurationManager(config_dir=Path(temp_dir))
        
        # Save the generated config
        manager.save_config(config)
        
        # Create a new manager instance to ensure we're loading from disk
        new_manager = ConfigurationManager(config_dir=Path(temp_dir))
        loaded_config = new_manager.load_config()
        
        # Verify persistence
        assert loaded_config == config
