"""Core exception classes for the Document Processor GUI."""


class DocumentProcessorError(Exception):
    """Base exception class for all Document Processor errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"


class ProcessingError(DocumentProcessorError):
    """Exception raised during document processing operations."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message, "PROCESSING_ERROR")
        self.file_path = file_path
        self.operation = operation
        self.details.update({
            "file_path": file_path,
            "operation": operation
        })


class ValidationError(DocumentProcessorError):
    """Exception raised during input validation."""
    
    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value
        self.details.update({
            "field": field,
            "value": str(value) if value is not None else None
        })


class FileSystemError(DocumentProcessorError):
    """Exception raised for file system related errors."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message, "FILESYSTEM_ERROR")
        self.file_path = file_path
        self.operation = operation
        self.details.update({
            "file_path": file_path,
            "operation": operation
        })


class DependencyError(DocumentProcessorError):
    """Exception raised when required dependencies are missing or invalid."""
    
    def __init__(self, message: str, dependency: str = None, version: str = None):
        super().__init__(message, "DEPENDENCY_ERROR")
        self.dependency = dependency
        self.version = version
        self.details.update({
            "dependency": dependency,
            "version": version
        })


class ConfigurationError(DocumentProcessorError):
    """Exception raised for configuration related errors."""
    
    def __init__(self, message: str, config_key: str = None, config_value=None):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.config_key = config_key
        self.config_value = config_value
        self.details.update({
            "config_key": config_key,
            "config_value": str(config_value) if config_value is not None else None
        })