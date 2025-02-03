"""Terminal formatting and utilities"""


import os
import sys
from typing import Literal, TypedDict, Union
from termcolor import colored


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


def create_line(text: str = "", char: str = "=", modified: int = 0) -> str:
    """Creates a line

    :param text: The text to underline/line. defaults to ""
    :type text: str
    :param char: The character to create line with, defaults to "="
    :type char: str, optional
    :param modified: The additional/less characters in line,
        defaults to 0
    :type modified: int
    :return: _A line using both the text length and modified value
    :rtype: str
    """
    tmp = [char] * (len(text) + modified)
    return "".join(tmp)


# ----------------------------------------------------------------------
# Formatting
# ----------------------------------------------------------------------


class TerminalCSS(TypedDict):
    """The CSS definition for a terminal. This should match the settings
    file terminal.css.
    """
    error: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                   'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                   'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                   'light_cyan', 'white']
    error_dark: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                        'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                        'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                        'light_cyan', 'white']
    build: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                   'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                   'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                   'light_cyan', 'white']
    build_dark: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                        'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                        'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                        'light_cyan', 'white']
    emphasis: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                      'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                      'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                      'light_cyan', 'white']
    emphasis_dark: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                           'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                           'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                           'light_cyan', 'white']
    execution: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                       'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                       'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                       'light_cyan', 'white']
    execution_dark: Literal['black', 'grey', 'red', 'green', 'yellow', 'blue',
                            'magenta', 'cyan', 'light_grey', 'dark_grey', 'light_red',
                            'light_green', 'light_yellow', 'light_blue', 'light_magenta',
                            'light_cyan', 'white']


DEFAULT_TERMINAL_CSS = TerminalCSS(
    error="red",
    error_dark="red",
    build="light_blue",
    build_dark="light_blue",
    execution="green",
    execution_dark="light_green",
    emphasis="cyan",
    emphasis_dark="light_cyan")


def prepare_string(
    text: str,
    css: Literal["error", "build", "emphasis", "none"],
    terminal_css: Union[TerminalCSS, None] = None,
    dark_mode: bool = False
) -> str:
    """Formats a string based on the curent CSS and dark mode. It uses
    The values in the settings file to allow for user to easily override
    and maps to the css value so the user can easily 

    :param text: the text to format
    :type text: str
    :param css: The CSS to format against
    :type css: Literal["error", "build", "emphasis", "none"]
    :param css_def: the CSS definition to use, defaults to None
    :type css_def: Union[TerminalCSS, None], optional
    :param dark_mode: use the dark mode value, defaults to False
    :type dark_mode: bool, optional
    :return: color formatted string
    :rtype: str
    """
    if terminal_css is None:
        terminal_css = DEFAULT_TERMINAL_CSS

    match css:
        case "none":
            return text
        case "error":
            if dark_mode:
                return colored(text, color=terminal_css["error_dark"])
            return colored(text, color=terminal_css["error"])
        case "build":
            if dark_mode:
                return colored(text, color=terminal_css["build_dark"])
            return colored(text, color=terminal_css["build"])
        case "emphasis":
            if dark_mode:
                return colored(
                    text, color=terminal_css["emphasis_dark"], attrs=["bold"])
            return colored(text, color=terminal_css["emphasis"], attrs=["bold"])
        case _:
            return text
