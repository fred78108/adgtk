"""CLI utilities are intende to improve overall UX"""

import logging
import sys
import os
from typing import Literal, Union
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
        for validator in self.validators:
            validator.validate(document)


class IntValidator(Validator):
    """Used for validating an entry is an Integer"""

    def validate(self, document):
        text = document.text

        try:
            int(text)
        except ValueError:
            raise ValidationError(
                message='Invalid entry. Input is Interger only')


class FloatValidator(Validator):
    """Used for validating an entry is an Float"""

    def validate(self, document):
        text = document.text

        try:
            float(text)
        except ValueError:
            raise ValidationError(
                message='Invalid entry. Input is Float only')


class NoWhitespaceValidator(Validator):
    """Used for validating an entry does not have a space"""

    def validate(self, document):
        text = document.text

        if " " in text:
            raise ValidationError(message='Invalid entry. Space observed')


class MinValueValidator(Validator):
    """Min value checks"""

    def __init__(self, min_value: Union[int, float]):
        self.min_value = min_value
        super().__init__()

    def validate(self, document):
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
        text = document.text

        if len(text) < self.min_length:
            raise ValidationError(message='Invalid entry. Too short')


class MaxLengthValidator(Validator):
    """Used for validating an entry does not exceed a length"""

    def __init__(self, max_length: int):
        self.max_length = max_length
        super().__init__()

    def validate(self, document):
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
        text = document.text

        if text not in self.choices:
            raise ValidationError(message=self.error_msg)


# ---------------------- UX ---------------------

def bottom_toolbar(
    helper: Union[str, None] = None,
    configuring: Union[str, None] = None,
    choices: Union[list, None] = None
) -> HTML:
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
    if wrap_count > 0:
        return " " * (width - 3) + "-> "
    else:
        return (": ").rjust(width)

# ----------------------------------------------------------------------
# intended to be used by other, "public" funcs
# ----------------------------------------------------------------------


def get_user_input(
    request: str,
    requested: Literal["float", "str", "int", "bool", "ml-str"],
    configuring: Union[str, None] = None,
    helper: Union[str, None] = None,
    choices: Union[list, None] = None,
    allow_whitespace: bool = True,
    default_selection: Union[float, str, int, bool, None] = None,
    max_characters: Union[int, None] = None,
    min_characters: Union[int, None] = None,
    min_value: Union[int, None] = None,
    max_value: Union[int, None] = None
) -> Union[str, int, float, bool]:

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

    # multi-line is a bit different of an experience
    if requested == "ml-str":
        # multi-line entries are a bit different in how its handled.
        print("Press [Esc] followed by [Enter] to complete input")
        print()
        print(request)
        line = create_line(text=request, char="-")
        print(line)

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
    request += " : "
    if requested == "int":
        if default_selection is not None:
            value = int(
                prompt(
                    request,
                    default=str(default_selection),
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices),
                    validator=MultiValidator(validators)))
        else:
            value = int(
                prompt(
                    request,
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices),
                    validator=MultiValidator(validators)))
    elif requested == "float":
        if default_selection is not None:

            value = float(prompt(
                request,
                default=str(default_selection),
                bottom_toolbar=bottom_toolbar(
                    helper=helper,
                    configuring=configuring,
                    choices=choices),
                validator=MultiValidator(validators)))
        else:
            value = float(
                prompt(
                    request,
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices),
                    validator=MultiValidator(validators)))
    elif requested == "str":
        if default_selection is not None:
            if choices is not None:
                request_completer = WordCompleter(choices, ignore_case=True)
                value = prompt(
                    request,
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
                    request,
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
                    request,
                    completer=request_completer,
                    complete_while_typing=True,
                    validator=MultiValidator(validators),
                    bottom_toolbar=bottom_toolbar(
                        helper=helper,
                        configuring=configuring,
                        choices=choices))
            else:
                value = prompt(
                    request,
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
    result = get_user_input(
        configuring=configuring,
        request=f"Action [{configuring}] ",
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
    title:Union[str, None] = None
) -> str:
    """Creates a line

    :param text: The text to underline/line. defaults to ""
    :type text: str
    :param char: The character to create line with, defaults to "="
    :type char: str, optional
    :param modified: The additional/less characters in line,
        defaults to 0
    :type modified: int
    :param title: The title to add to the line, defaults to None
    :type title: Union[str, None]
    :return: _A line using both the text length and modified value
    :rtype: str
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
