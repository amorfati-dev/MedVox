"""
Custom exception classes for dental documentation processing
"""


class DocumentationError(Exception):
    """Base exception for documentation processing errors"""
    pass


class ProcessingTimeoutError(DocumentationError):
    """Raised when processing takes too long"""
    pass


class InsufficientDataError(DocumentationError):
    """Raised when there's not enough data to process"""
    pass


class InvalidFormatError(DocumentationError):
    """Raised when data format is invalid"""
    pass 