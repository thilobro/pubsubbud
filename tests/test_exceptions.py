"""Tests for the exceptions module."""

from pubsubbud.exceptions import ValidationError


def test_validation_error():
    """Test the ValidationError exception."""
    # Test basic instantiation
    error = ValidationError("Test error")
    assert str(error) == "Test error"

    # Test with multiple messages
    error = ValidationError(["Error 1", "Error 2"])
    assert str(error) == "['Error 1', 'Error 2']"

    # Test with multiple arguments
    error = ValidationError("Custom message", "Error details")
    assert str(error) == "('Custom message', 'Error details')"

    # Test inheritance
    assert isinstance(error, Exception)
