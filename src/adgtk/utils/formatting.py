"""
Used for dealing with formatting and parsing of strings.
"""

import datetime
import yaml
from yaml import YAMLError


# py -m pytest -s test/utils/test_formatting.py


# ----------------------------------------------------------------------
# Module Configurations
# ----------------------------------------------------------------------
DEBUG = False


# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------

class UnableToProcess(Exception):
    """Used for failing to process and wanting to degrade gracefully"""

    default_msg = "Unable to process."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


# ----------------------------------------------------------------------
# Common data representations
# ----------------------------------------------------------------------


def get_timestamp_now(include_time: bool = True) -> str:
    """Generates a string with a timestamp. The goal is to have a
    consistent data and date/time format across the different reports,
    etc.

    Args:
        include_time (bool, optional): Include time?.
            Defaults to True.

    Returns:
        str: A timestamp string formatted for reports, etc.
    """
    now = datetime.datetime.now()
    if include_time:
        return now.strftime("%d/%m/%y at %H:%M:%S")
    else:
        return now.strftime("%d/%m/%y")

# ---------------------------------------------------------------------
# YAML / LLM text processing
# ---------------------------------------------------------------------


def count_prefix_spaces(text: str) -> int:
    cleaned = text
    return len(text) - len(cleaned.strip())


def process_possible_yaml(text: str) -> list:
    """Provides a first attempt at processing YAML. This is ideal when
    the text is properly formatted and a single entry. If direct
    processing fails then this function invokes an attempt to cleanup
    and process that text. This should be invoked as a first attempt for
    text that is likely yaml or at least processable via yaml.

    :param text: the text to process as potential yaml
    :type text: str
    :return: a list of dict that contains the results of processing.
    :rtype: list
    """
    try:
        entry = []
        data = yaml.safe_load(text)
        if data is not None:
            # So its a single entry, convert to list in order to return.
            entry.append(data)
            return entry
    except YAMLError:
        # the root error. uncomment and expand/print as needed below to
        # troubleshoot or learn more.
        # https://pyyaml.org/wiki/PyYAMLDocumentation
        pass
    except yaml.scanner.ScannerError:
        # observed with synthetic data.
        pass
    except yaml.constructor.ConstructorError:
        # can occur if the LLM does something like
        # age: !binary ...
        pass
    except yaml.parser.ParserError:
        pass
    except yaml.composer.ComposerError:
        # may be triggered by ---, observed in the wild
        pass
    except AttributeError:
        pass

    # so we hit a processing error. try again with
    return clean_and_process_possible_yaml(text)


def clean_and_process_possible_yaml(text: str) -> list:
    """cleans up via some simple pre-determined rules and attempts to
    locate and process yaml entries in text. This is useful for when
    there are multiple entries interlaced with text such as when a LLM
    adds text such as "and here is another...", etc. Best practice is to
    run process_possible_yaml and let it invokes this function.

    :param text: the text to process as potential yaml
    :type text: str
    :return: a list of dict that contains the results of processing.
    :rtype: list
    """
    buffer = ""
    results = []
    lines = text.splitlines(keepends=True)
    offset = 0

    # build the buffer
    for line in lines:
        if ":" in line:
            # validate and load the buffer?
            split_out = line.split(":")
            if len(split_out) == 2:
                second_split = split_out[0].split()
                if len(second_split) == 1:
                    # only valid space is a prefix
                    if len(buffer) == 0:
                        # get the offset. This can occur when the output
                        # uses a "tab" to offset text from the examle.
                        # By using an offset the function cleans up this
                        # extra and unexpected spacing.
                        offset = count_prefix_spaces(line)
                        offset -= 1     # so we slice cleanly

                    # process w/offset
                    if offset > 0 and line.startswith(" "):
                        line = line[offset:]

                    # extra formatting needed
                    if line.rstrip().endswith(","):
                        remove = True
                        if line.startswith("'"):
                            remove = False
                        if line.startswith('"'):
                            remove = False

                        if remove:
                            # remove the comma.
                            line = line[:-2]
                            line += "\n"    # and add back in the CR
                    buffer += line
                elif "-" in second_split:
                    # handling of a list object.
                    if len(buffer) > 0:
                        if len(second_split) == 2:
                            buffer += line
        else:
            # process the buffer
            try:
                # safety to confirm buffer is not None and > 3.
                if isinstance(buffer, str):
                    if len(buffer) > 3:
                        data = yaml.safe_load(buffer)
                        if data is not None:
                            results.append(data)
            except YAMLError:
                # the root error. uncomment and expand/print as needed below to
                # troubleshoot or learn more.
                # https://pyyaml.org/wiki/PyYAMLDocumentation
                pass
            except yaml.scanner.ScannerError:
                # observed with synthetic data.
                pass
            except yaml.constructor.ConstructorError:
                # can occur if the LLM does something like
                # age: !binary ...
                pass
            except yaml.parser.ParserError as e:
                pass
                # uncomment to debug and develop. Its normal and
                # expected though to have parse errors with output from
                # a llm though. so this is a NO-OP.
                # raise yaml.parser.ParserError from e
            except yaml.composer.ComposerError:
                # may be triggered by ---, observed in the wild
                pass
            except AttributeError:
                pass

            # and reset buffer if more
            buffer = ""

    return results
