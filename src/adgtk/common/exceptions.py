"""Common exceptions for the ADGTK package"""


class InvalidScenarioState(Exception):
    """Used for any scenario state that is invalid"""

    default_msg = "Invalid Scenario state."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


class InsufficientData(Exception):
    """Used when there is insufficient data to perform an operation"""

    default_msg = "Insufficient data."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


class InvalidConfigException(Exception):
    """Used for any situation where the configuration is not valid"""
    default_msg = 'Invalid configuration'

    def __init__(self, message:str = default_msg):
        super().__init__(message)



class DuplicateFactoryRegistration(Exception):
    """Used for registration collision"""

    default_msg = "Registration exists. Unregister first."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


class InvalidBlueprint(Exception):
    """Used when a blueprint is invalid. Covers both a FactoryBlueprint
    as well as any future blueprints."""

    default_msg = "Invalid Blueprint."

    def __init__(self, message: str = default_msg):
        super().__init__(message)
