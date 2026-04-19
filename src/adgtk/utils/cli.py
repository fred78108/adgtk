"""CLI utilities are intende to improve overall UX"""

import logging
import os
import sys
from typing import Literal, Optional, Union
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML


# ----------------------------------------------------------------------
# not intended for exposing via init, etc. module specific func
# ----------------------------------------------------------------------


# ---------------------- Validation ---------------------
class MultiValidator(Validator):

    def __init__(self, validators: list):
        self.validators = validators

    def validate(self, document):
        """Runs all validators against the document.

        Args:
            document: The document to validate.
        """
        for validator in self.validators:
            validator.validate(document)


class IntValidator(Validator):
    """Used for validating an entry is an Integer"""

    def validate(self, document):
        """Validates that the text is an integer.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the text is not an integer.
        """
        text = document.text

        try:
            int(text)
        except ValueError:
            raise ValidationError(
                message='Invalid entry. Input is Interger only')


class FloatValidator(Validator):
    """Used for validating an entry is an Float"""

    def validate(self, document):
        """Validates that the text is a float.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the text is not a float.
        """
        text = document.text

        try:
            float(text)
        except ValueError:
            raise ValidationError(
                message='Invalid entry. Input is Float only')


class NoWhitespaceValidator(Validator):
    """Used for validating an entry does not have a space"""

    def validate(self, document):
        """Validates that the text contains no whitespace.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the text contains a space.
        """
        text = document.text

        if " " in text:
            raise ValidationError(message='Invalid entry. Space observed')


class MinValueValidator(Validator):
    """Min value checks"""

    def __init__(self, min_value: Union[int, float]):
        self.min_value = min_value
        super().__init__()

    def validate(self, document):
        """Validates that the numeric value meets a minimum threshold.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the value is below the minimum.
        """
        text = document.text

        try:
            val = float(text)
            if val < self.min_value:
                raise ValidationError(message="too small a value")
        except ValueError:
            # number checks is another validator
            pass


class MaxValueValidator(Validator):
    """Max value checks"""

    def __init__(self, max_value: Union[int, float]):
        self.max_value = max_value
        super().__init__()

    def validate(self, document):
        """Validates that the numeric value does not exceed a maximum.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the value is above the maximum.
        """
        text = document.text

        try:
            val = float(text)
            if val > self.max_value:
                raise ValidationError(message="too large a value")
        except ValueError:
            # number checks is another validator
            pass


class MinLengthValidator(Validator):
    """Used for validating an entry has a minimum length"""

    def __init__(self, min_length: int):
        self.min_length = min_length
        super().__init__()

    def validate(self, document):
        """Validates that the text meets a minimum length requirement.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the text is too short.
        """
        text = document.text

        if len(text) < self.min_length:
            raise ValidationError(message='Invalid entry. Too short')


class MaxLengthValidator(Validator):
    """Used for validating an entry does not exceed a length"""

    def __init__(self, max_length: int):
        self.max_length = max_length
        super().__init__()

    def validate(self, document):
        """Validates that the text does not exceed a maximum length.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the text is too long.
        """
        text = document.text

        if len(text) > self.max_length:
            raise ValidationError(message='Invalid entry. Too long')


class ChoiceValidator(Validator):
    """Used for validating the user input is expected based on choices.
    """

    def __init__(self, choices: list):
        self.choices = choices
        choice_str = " ".join(choices)
        self.error_msg = f"Valid options are : {choice_str}"
        super().__init__()

    def validate(self, document):
        """Validates that the text is one of the allowed choices.

        Args:
            document: The document to validate.

        Raises:
            ValidationError: If the text is not in the allowed choices.
        """
        text = document.text

        if text not in self.choices:
            raise ValidationError(message=self.error_msg)


# ---------------------- UX ---------------------

def bottom_toolbar(
    helper: Union[str, None] = None,
    configuring: Union[str, None] = None,
    choices: Union[list, None] = None
) -> HTML:
    """Generates the bottom toolbar HTML for the prompt.

    Args:
        helper (str, optional): A helper message to display.
        configuring (str, optional): The name of the item being configured.
        choices (list, optional): A list of valid choices.

    Returns:
        HTML: The formatted HTML for the toolbar.
    """
    html_str = ""
    if configuring is not None:
        html_str += f"Configuring [{configuring}] "

    if helper is not None:
        html_str += f'<b><style bg="ansired">{helper}</style></b>!'

    if choices is not None:
        if len(choices) > 4:
            choice_str = ",".join(choices[0:3])
            choice_str += " ..."
        else:
            choice_str = ", ".join(choices)

        if len(choice_str) > 50:
            choice_str = choices[0]
            choice_str += " ..."

        if not html_str.endswith("."):
            html_str += "."

        html_str += ' Valid choices are : <b><style bg="ansired">'
        html_str += f'{choice_str}</style></b>'

    return HTML(html_str)


def prompt_continuation(width, line_number, wrap_count):
    """Handles visual continuation for multiline prompts.

    Args:
        width (int): The width of the prompt area.
        line_number (int): The current line number.
        wrap_count (int): How many times the line has wrapped.

    Returns:
        str: The continuation string.
    """
    if wrap_count > 0:
        return " " * (width - 3) + "-> "
    else:
        return (": ").rjust(width)

# ----------------------------------------------------------------------
# intended to be used by other, "public" funcs
# ----------------------------------------------------------------------


def get_user_input(
    user_prompt: str,
    requested: Literal["float", "str", "int", "bool", "ml-str"],
    configuring: Union[str, None] = None,
    helper: Union[str, None] = None,
    choices: Union[list, None] = None,
    allow_whitespace: bool = True,
    default_selection: Union[float, str, int, bool, None] = None,
    max_characters: Union[int, None] = None,
    min_characters: Union[int, None] = None,
    min_value: Union[int, None] = None,
    max_value: Union[int, None] = None,
    limit_ml_line_length: Optional[int] = None
) -> Union[str, int, float, bool]:
    """Prompts the user for input with validation and UI features.

    Args:
        user_prompt (str): The message to display to the user.
        requested (Literal["float", "str", "int", "bool", "ml-str"]):
            The expected data type for the input.
        configuring (str, optional): Name of the item being configured.
        helper (str, optional): Help text for the bottom toolbar.
        choices (list, optional): List of valid string options.
        allow_whitespace (bool): Whether spaces are allowed in input.
            Defaults to True.
        default_selection (Union[float, str, int, bool, None]): Default
            value if input is empty.
        max_characters (int, optional): Maximum input length.
        min_characters (int, optional): Minimum input length.
        min_value (int, optional): Minimum numeric value.
        max_value (int, optional): Maximum numeric value.
        limit_ml_line_length (int, optional): Max line length for
            multi-line input.

    Returns:
        Union[str, int, float, bool]: The validated user input.

    Raises:
        ValueError: If input is invalid and no default is provided.
    """

    # if default_selection is not None:
    #    request += f" [{default_selection}] : "
    # else:

    validators: list[Validator] = []
    value: Union[str, int, float, bool] = ""

    if choices is not None:
        validators.append(ChoiceValidator(choices))
    if allow_whitespace is False:
        validators.append(NoWhitespaceValidator())
    if min_value is not None:
        validators.append(MinValueValidator(min_value))
    if max_value is not None:
        validators.append(MaxValueValidator(max_value))
    if min_characters is not None:
        validators.append(MinLengthValidator(min_characters))
    if max_characters is not None:
        validators.append(MaxLengthValidator(max_characters))
    if requested == "int":
        validators.append(IntValidator())
    elif requested == "float":
        validators.append(FloatValidator())
    elif requested == "bool":
        # the list should match below
        validators.append(ChoiceValidator(["True", "False"]))

    # multi-line is a bit different of an experience
    if requested == "ml-str":
        # multi-line entries are a bit different in how its handled.
        print(user_prompt)
        line = create_line(text=user_prompt, char="-")
        if limit_ml_line_length is not None:
            if len(line) > limit_ml_line_length:
                line = create_line(text="-", modified=limit_ml_line_length)
        print(line)
        print("Press [Esc] followed by [Enter] to complete input")
        print()

        value = prompt(
            "input : ",
            prompt_continuation=prompt_continuation,
            multiline=True,
            bottom_toolbar=bottom_toolbar(
                helper=helper,
                configuring=configuring))
        # going ahead and returning since its a string and ready
        return value

    # others
    user_prompt += " : "
    if requested == "int":
        if default_selection is not None:
            value = int(
                prompt(
                    user_prompt,
                    default=str(default_selection),
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices),
                    validator=MultiValidator(validators)))
        else:
            value = int(
                prompt(
                    user_prompt,
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices),
                    validator=MultiValidator(validators)))
    elif requested == "float":
        if default_selection is not None:

            value = float(prompt(
                user_prompt,
                default=str(default_selection),
                bottom_toolbar=bottom_toolbar(
                    helper=helper,
                    configuring=configuring,
                    choices=choices),
                validator=MultiValidator(validators)))
        else:
            value = float(
                prompt(
                    user_prompt,
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices),
                    validator=MultiValidator(validators)))
    elif requested == "bool":
        choices = ["True", "False"]
        request_completer = WordCompleter(choices, ignore_case=True)

        default_str = "False"
        if default_selection is not None:
            default_str = "True" if default_selection else "False"

        value = prompt(
            user_prompt,
            default=default_str,
            completer=request_completer,
            complete_while_typing=True,
            validator=MultiValidator(validators),
            bottom_toolbar=bottom_toolbar(
                helper=helper,
                configuring=configuring,
                choices=choices)
        )

        # Normalize input and convert to boolean
        value = value.strip().lower()
        if value == "true":
            return True
        elif value == "false":
            return False
        else:
            raise ValueError(
                "Invalid input for boolean. Expected 'True' or 'False'.")

    elif requested == "str":
        if default_selection is not None:
            if choices is not None:
                request_completer = WordCompleter(choices, ignore_case=True)
                value = prompt(
                    user_prompt,
                    default=str(default_selection),
                    completer=request_completer,
                    complete_while_typing=True,
                    validator=MultiValidator(validators),
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices))

            else:
                value = prompt(
                    user_prompt,
                    default=str(default_selection),
                    validator=MultiValidator(validators),
                    complete_while_typing=True,
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices))
        else:
            if choices is not None:
                request_completer = WordCompleter(choices, ignore_case=True)
                value = prompt(
                    user_prompt,
                    completer=request_completer,
                    complete_while_typing=True,
                    validator=MultiValidator(validators),
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices))
            else:
                value = prompt(
                    user_prompt,
                    validator=MultiValidator(validators),
                    complete_while_typing=True,
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices))

    else:
        if requested != "ml-str":
            logging.error(f"Unexpected type {requested}")
        return 0

    if isinstance(value, str):
        if len(value) == 0:
            if default_selection is not None:
                return default_selection
            else:
                msg = "No value entered and no default provided"
                logging.error(msg)
                print(f"ERROR: {msg}. returning ``")
                return ""

    return value


def get_more_ask(configuring: Union[str, None] = None) -> bool:
    """Prompts the user to decide if they want to add more items or finish.

    Args:
        configuring (str, optional): The label of what is being configured.

    Returns:
        bool: True if the user chooses 'more', False if 'done'.
    """
    result = get_user_input(
        configuring=configuring,
        user_prompt=f"Action [{configuring}] ",
        requested="str",
        choices=["done", "more"])

    if result == "done":
        return False

    return True


# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------


def clear_screen():
    """Clears the screen in the terminal.
    """
    if sys.platform.startswith("win"):
        os.system("cls")
    else:
        print("\033c")


def create_line(
    text: str = "",
    char: str = "=",
    modified: int = 0,
    title: Union[str, None] = None
) -> str:
    """Creates a line

    Args:
        text (str): The text to underline/line. Defaults to "".
        char (str): The character to create line with. Defaults to "=".
        modified (int): Additional/fewer characters in line. Defaults to 0.
        title (str, optional): The title to add to the line. Defaults to None.

    Returns:
        str: A line using both the text length and modified value.
    """
    target_length = len(text) + modified

    if title is not None:
        tmp = [char] * ((int(target_length/2) - int(len(title)/2) - 1))
        line = "".join(tmp)
        line += f" {title.upper()} "
        line = "".join(tmp)
        if len(tmp) < target_length:
            line += char
        return line
    else:
        tmp = [char] * target_length
        return "".join(tmp)
