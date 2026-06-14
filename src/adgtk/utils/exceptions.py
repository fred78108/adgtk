"""Common exceptions for the ADGTK package"""

from typing import Optional


class ActiveTaskFound(Exception):
    """Raise when there is an attempt is made to start a second experiment.
    """
    def __init__(self, message: Optional[str] = None):
        if message is None:
            message = "Active experiment is already running"
        super().__init__(message)


class UnableToMeasureException(Exception):
    """Raise when there is an invalid configuration."""
    def __init__(self, message: Optional[str] = None):
        if message is None:
            message = "Unable to measure the data"
        super().__init__(message)
