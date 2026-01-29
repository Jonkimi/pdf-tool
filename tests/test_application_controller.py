"""Unit tests for ApplicationController."""

import pytest
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from document_processor_gui.config.config_manager import ConfigurationManager, AppConfig
from document_processor_gui.core.application_controller import ApplicationController
from document_processor_gui.core.error_handler import ErrorHandler
from document_processor_gui.core.language_manager import LanguageManager
from document_processor_gui.processing.models import ProcessingResult, ProcessingResults


class TestApplicationController:
    """Tests for ApplicationController class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create a ConfigurationManager with temp directory."""
        manager = ConfigurationManager(config_dir=temp_config_dir)
        manager.load_config()
        return manager

    @pytest.fixture
    def controller(self, config_manager):
        """Create an ApplicationController."""
        return ApplicationController(config_manager)

    @pytest.fixture
    def controller_with_handlers(self, config_manager):
        """Create an ApplicationController with error and language handlers."""
        error_handler = ErrorHandler()
        language_manager = LanguageManager(config_manager)
        return ApplicationController(
            config_manager,
            error_handler=error_handler,
            language_manager=language_manager
        )

    def test_initialization(self, controller):
        """Test controller initializes correctly."""
        assert controller.config_manager is not None
        assert controller._is_processing is False
        assert controller._cancel_requested is False

    def test_is_processing_property(self, controller):
        """Test is_processing property."""
        assert controller.is_processing is False

    def test_set_callbacks(self, controller):
        """Test setting callbacks."""
        progress_cb = Mock()
        completion_cb = Mock()
        error_cb = Mock()

        controller.set_callbacks(
            progress_callback=progress_cb,
            completion_callback=completion_cb,
            error_callback=error_cb
        )

        assert controller._progress_callback is progress_cb
        assert controller._completion_callback is completion_cb
        assert controller._error_callback is error_cb

    def test_get_settings(self, controller):
        """Test getting settings as dictionary."""
        settings = controller.get_settings()

        assert isinstance(settings, dict)
        assert 'language' in settings
        assert 'compression_level' in settings
        assert settings['language'] == 'zh'

    def test_update_settings(self, controller):
        """Test updating settings."""
        result = controller.update_settings(language='en')

        assert result is True
        config = controller.config_manager.get_config()
        assert config.language == 'en'

    def test_update_settings_invalid_key(self, controller):
        """Test updating with invalid setting key."""
        error_cb = Mock()
        controller.set_callbacks(error_callback=error_cb)

        result = controller.update_settings(invalid_key='value')

        assert result is False
        assert error_cb.called

    def test_reset_settings(self, controller):
        """Test resetting settings to defaults."""
        # First change a setting
        controller.update_settings(language='en')
        assert controller.config_manager.get_config().language == 'en'

        # Reset
        result = controller.reset_settings()

        assert result is True
        assert controller.config_manager.get_config().language == 'zh'

    def test_request_cancel_when_not_processing(self, controller):
        """Test requesting cancel when not processing."""
        controller.request_cancel()
        # Should not raise, just log
        assert controller._cancel_requested is False  # Not processing, so flag not set

    def test_validate_files_word(self, controller, temp_config_dir):
        """Test validating Word files."""
        # Create test files
        word_file = temp_config_dir / "test.docx"
        word_file.touch()
        pdf_file = temp_config_dir / "test.pdf"
        pdf_file.touch()
        nonexistent = str(temp_config_dir / "nonexistent.docx")

        result = controller.validate_files(
            [str(word_file), str(pdf_file), nonexistent],
            file_type="word"
        )

        assert str(word_file) in result['valid_files']
        assert str(pdf_file) in result['invalid_files']
        assert nonexistent in result['invalid_files']
        assert len(result['errors']) == 2

    def test_validate_files_pdf(self, controller, temp_config_dir):
        """Test validating PDF files."""
        pdf_file = temp_config_dir / "test.pdf"
        pdf_file.touch()
        word_file = temp_config_dir / "test.docx"
        word_file.touch()

        result = controller.validate_files(
            [str(pdf_file), str(word_file)],
            file_type="pdf"
        )

        assert str(pdf_file) in result['valid_files']
        assert str(word_file) in result['invalid_files']

    def test_validate_files_any(self, controller, temp_config_dir):
        """Test validating any files."""
        file1 = temp_config_dir / "test.txt"
        file1.touch()
        file2 = temp_config_dir / "test.pdf"
        file2.touch()

        result = controller.validate_files(
            [str(file1), str(file2)],
            file_type="any"
        )

        assert len(result['valid_files']) == 2
        assert len(result['invalid_files']) == 0

    def test_check_dependencies(self, controller):
        """Test checking dependencies."""
        status = controller.check_dependencies()

        assert 'ghostscript' in status
        assert 'docx2pdf' in status
        assert 'pymupdf' in status

        # Each should have expected keys
        for dep in status.values():
            assert 'available' in dep
            assert 'error' in dep

    def test_get_text_with_language_manager(self, controller_with_handlers):
        """Test getting localized text."""
        text = controller_with_handlers.get_text('app_title')
        assert text != 'app_title'  # Should be translated

    def test_get_text_without_language_manager(self, controller):
        """Test getting text without language manager."""
        text = controller.get_text('some.key')
        assert text == 'some.key'  # Returns key when no manager

    def test_set_language(self, controller_with_handlers):
        """Test changing language."""
        result = controller_with_handlers.set_language('en')
        assert result is True

    def test_set_language_without_manager(self, controller):
        """Test changing language without manager."""
        result = controller.set_language('en')
        assert result is False

    def test_cannot_start_operation_while_processing(self, controller):
        """Test that operations cannot start while another is in progress."""
        controller._is_processing = True

        result1 = controller.start_conversion(['file.docx'], '/output')
        result2 = controller.start_compression(['file.pdf'], '/output')
        result3 = controller.start_labeling(['file.pdf'], '/output')

        assert result1 is False
        assert result2 is False
        assert result3 is False

    @patch('document_processor_gui.core.application_controller.ConversionEngine')
    @patch('document_processor_gui.core.application_controller.WordConverter')
    @patch('document_processor_gui.core.application_controller.GhostscriptWrapper')
    @patch('document_processor_gui.core.application_controller.PDFLabeler')
    def test_start_conversion_initializes_engines(
        self, mock_labeler, mock_gs, mock_word, mock_engine, controller
    ):
        """Test that starting conversion initializes engines."""
        mock_instance = Mock()
        mock_engine.return_value = mock_instance

        # Mock the convert_files to return immediately
        results = ProcessingResults()
        mock_instance.convert_files.return_value = results

        controller.start_conversion(['test.docx'], '/output')

        # Wait a bit for thread to start
        time.sleep(0.1)

        # Engines should be initialized
        assert mock_word.called
        assert mock_gs.called
        assert mock_labeler.called
        assert mock_engine.called


class TestApplicationControllerOperations:
    """Tests for processing operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def controller_with_mocks(self, temp_dir):
        """Create controller with mocked engines."""
        config_manager = ConfigurationManager(config_dir=temp_dir)
        config_manager.load_config()
        controller = ApplicationController(config_manager)

        # Create mock engines
        controller._conversion_engine = Mock()
        controller._compression_engine = Mock()
        controller._labeling_engine = Mock()

        # Mark backends as initialized
        controller._word_converter = Mock()
        controller._gs_wrapper = Mock()
        controller._pdf_labeler = Mock()

        return controller

    def test_operation_progress_callback(self, controller_with_mocks):
        """Test that progress callback is called."""
        progress_calls = []

        def progress_cb(current, total, filename):
            progress_calls.append((current, total, filename))

        completion_event = threading.Event()

        def completion_cb(results):
            completion_event.set()

        controller_with_mocks.set_callbacks(
            progress_callback=progress_cb,
            completion_callback=completion_cb
        )

        # Setup mock to call progress callback
        def mock_convert(files, output_dir, settings, callback):
            if callback:
                callback(1, 1, 'test.docx')
            return ProcessingResults()

        controller_with_mocks._conversion_engine.convert_files = mock_convert

        controller_with_mocks.start_conversion(['test.docx'], '/output')

        # Wait for completion
        completion_event.wait(timeout=2)

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1, 'test.docx')

    def test_operation_completion_callback(self, controller_with_mocks):
        """Test that completion callback is called with results."""
        completion_results = []
        completion_event = threading.Event()

        def completion_cb(results):
            completion_results.append(results)
            completion_event.set()

        controller_with_mocks.set_callbacks(completion_callback=completion_cb)

        # Setup mock
        expected_results = ProcessingResults()
        expected_results.add_result(ProcessingResult(
            success=True,
            input_file='test.docx',
            output_file='test.pdf'
        ))
        controller_with_mocks._compression_engine.compress_files.return_value = expected_results

        controller_with_mocks.start_compression(['test.pdf'], '/output')

        completion_event.wait(timeout=2)

        assert len(completion_results) == 1
        assert completion_results[0].successful_files == 1

    def test_operation_error_callback(self, controller_with_mocks):
        """Test that error callback is called on exception."""
        error_messages = []
        error_event = threading.Event()

        def error_cb(msg):
            error_messages.append(msg)
            error_event.set()

        controller_with_mocks.set_callbacks(error_callback=error_cb)

        # Setup mock to raise exception
        controller_with_mocks._labeling_engine.label_files.side_effect = Exception("Test error")

        controller_with_mocks.start_labeling(['test.pdf'], '/output')

        error_event.wait(timeout=2)

        assert len(error_messages) == 1
        assert "Test error" in error_messages[0]

    def test_generate_label_preview(self, controller_with_mocks):
        """Test generating label preview."""
        expected_bytes = b'PNG image data'
        controller_with_mocks._labeling_engine.generate_preview.return_value = expected_bytes

        result = controller_with_mocks.generate_label_preview('test.pdf')

        assert result == expected_bytes
        assert controller_with_mocks._labeling_engine.generate_preview.called

    def test_generate_label_preview_error(self, controller_with_mocks):
        """Test preview generation error handling."""
        error_messages = []
        controller_with_mocks.set_callbacks(error_callback=lambda msg: error_messages.append(msg))
        controller_with_mocks._labeling_engine.generate_preview.side_effect = Exception("Preview failed")

        result = controller_with_mocks.generate_label_preview('test.pdf')

        assert result is None
        assert len(error_messages) == 1


class TestApplicationControllerCancellation:
    """Tests for operation cancellation."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def controller_with_slow_mock(self, temp_dir):
        """Create controller with a slow mock operation."""
        config_manager = ConfigurationManager(config_dir=temp_dir)
        config_manager.load_config()
        controller = ApplicationController(config_manager)

        controller._word_converter = Mock()
        controller._gs_wrapper = Mock()
        controller._pdf_labeler = Mock()

        controller._conversion_engine = Mock()
        controller._compression_engine = Mock()
        controller._labeling_engine = Mock()

        return controller

    def test_request_cancel_during_processing(self, controller_with_slow_mock):
        """Test that cancellation request is tracked."""
        started_event = threading.Event()
        cancel_detected = []

        def slow_operation(files, output_dir, settings, callback):
            started_event.set()
            # Check for cancellation in a loop
            for i in range(10):
                time.sleep(0.1)
                try:
                    if callback:
                        callback(i, 10, f'file{i}')
                except InterruptedError:
                    cancel_detected.append(True)
                    raise
            return ProcessingResults()

        controller_with_slow_mock._compression_engine.compress_files = slow_operation

        completion_event = threading.Event()
        controller_with_slow_mock.set_callbacks(
            completion_callback=lambda r: completion_event.set()
        )

        controller_with_slow_mock.start_compression(['test.pdf'], '/output')

        # Wait for operation to start
        started_event.wait(timeout=1)

        # Request cancellation
        controller_with_slow_mock.request_cancel()

        # Wait for completion
        completion_event.wait(timeout=3)

        assert len(cancel_detected) == 1
        assert controller_with_slow_mock._is_processing is False
