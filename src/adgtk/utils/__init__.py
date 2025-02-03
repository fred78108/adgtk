"""Common Utils"""

from .cli import get_user_input, get_more_ask, create_line, clear_screen
from .formatting import (
    get_timestamp_now,
    process_possible_yaml,
    count_prefix_spaces)
from .logs import start_logging
from .plotting import plot_single_line
from .processing import (
    string_to_bool,
    get_pair_from_iterable,
    get_sample_from_iterable)
from .settings import load_settings
from .text import camel_case_generation
