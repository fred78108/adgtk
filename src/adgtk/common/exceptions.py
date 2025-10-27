"""Common exceptions for the ADGTK package"""

from typing import Optional

class UnableToMeasureException(Exception):
    """Raise when there is an invalid configuration."""
    def __init__(self, message: Optional[str]=None):
        if message is None:
            message = "Unable to measure the data"
        super().__init__(message)
