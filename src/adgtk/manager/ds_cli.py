"""Provides and ADGTK managed dataset inventory.

Status: MVP, just enough to get basic data parsing now.

ROADMAP
=======
1. loading of datasets from HuggingFace ds, other wrappers.
"""

import argparse
import os
import sys
# before importing others
# ----------------------------------------------------------------------
# Start of path verification
# ----------------------------------------------------------------------
path = os.getcwd()
bootstrap_file = os.path.join(path, "bootstrap.py")
if not os.path.exists(bootstrap_file):
    print("ERROR: Unable to locate the bootstrap.py. Please check your path.")
    sys.exit(1)
# ----------------------------------------------------------------------
# End of path verification
# ----------------------------------------------------------------------
print("Here for some reason?")
from typing import Literal, Optional, Union, cast
from adgtk.data.structure import (
    SUPPORTED_FILE_ENCODING_TYPES,
    FileEncodingTypes
)


from adgtk.data.dataset import DatasetManager
from adgtk.utils import get_user_input
from adgtk.utils import create_logger


_logger = create_logger(
    logfile="file.manager.log",
    subdir="common",
    logger_name=__name__
)




# ----------------------------------------------------------------------
# Constants - user facing strings
# ----------------------------------------------------------------------

INTRO = ("ADGTK-DS: Bringing a consistent interface for your datasets\n"
         "===========================================================\n"
         "The adgtk-ds is a utility script for managing the datasets \n"
         "used for experimentation. This provides the human researcher the \n"
         "ability to refer to a file id during experiments instead of \ndealing"
         " with the complexity of the different formats, ingestion, \n"
         "etc as part of normal data processing.\n"
         )

HELP_W_INTRO = f"""{INTRO}\n
To use this script:\n
$ adgtk-ds [command] [options]

command
-------
- register : registers a new file into the manager
- retire   : retires a file from the manager
- report   : generates a report to the screen

For register the following are valid arguments:
--file         : the file to register, if not passed the user is asked
--encoding     : the encoding of the file,, if not passed the user is asked
                  (valid: {SUPPORTED_FILE_ENCODING_TYPES})
--metadata     : The metadata file w/path
                  (example: file.csv has file.meta.json)
--use          : The use of the dataset. 
                  (valid: test, train, validate, other)

for retire the following are valid arguments:
--id : the id of the file to retire

For find the following are valid arguments:
--filename (required) : the filename to register (w/path)

So for example, to register a file to the school file manager:
$ python file_manager.py school register --f=data/demo.csv -e=csv

report
------
you can further filter a report by passing in tags. For example:
$ python file_manager.py report ground entity

- Filters the report to the entries that have both tags ground and entity
- If no tags are sent all files are reported

Logging
-------
The log is maintained at logs/common/dataset.manager.log
"""


# ----------------------------------------------------------------------
# helper functions
# ----------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parses the command line arguments

    Returns:
        argparse.Namespace: The command line input
    """
    parser = argparse.ArgumentParser()
    command_parser = parser.add_subparsers(
        dest="command", help="Command to perform")
    
    # Report subcommand
    report_parser = command_parser.add_parser(
        "report", help="Generate a report")
    report_parser.add_argument(
        "tags",
        nargs="*",
        help="Tag(s) to filter the report"
    )

    # Register subcommand
    register_parser = command_parser.add_parser(
        "register", help="Register a file")
    register_parser.add_argument(
        '-f', '--file',
        type=str,
        required=False,
        help="The full path to the file")
    register_parser.add_argument(
        '-e', '--encoding',
        type=str,
        required=False,
        choices=SUPPORTED_FILE_ENCODING_TYPES,
        help=f"The encoding of the file: {SUPPORTED_FILE_ENCODING_TYPES}")
    register_parser.add_argument(
        '-m', '--metadata',
        type=str,
        required=False,
        help="The full path to the metadata file")
    register_parser.add_argument(
        '--id',
        type=str,
        required=False,
        help="Optional custom ID to assign to the file entry"
    )
    register_parser.add_argument(
        "--use",
        type=str,
        choices=["test", "train", "validate", "other"],
        required=True,
        help="The use of the dataset",
        default="other"
    )

    # Retire subcommand
    retire_parser = command_parser.add_parser(
        "retire", help="Retire a file")
    retire_parser.add_argument(
        '--id', type=str, required=False, help="The file id")

    # Find subcommand
    find_parser = command_parser.add_parser("find", help="Find a file ID")
    find_parser.add_argument(
        '--filename', type=str, required=True, help="The filename")

    args = parser.parse_args()
    return args


def retire_file(file_tracker: DatasetManager, id: Optional[str] = None):

    if id is None:
        id = str(get_user_input(
            user_prompt="What is the file ID you would like to retire?",
            requested="str",
            helper="This is the internal file_id for the entry",
            allow_whitespace=False,
            min_characters=1
        ))
    try:
        file_tracker.retire_file(id)
    except IndexError as e:
        print(e)
        _logger.error(e)
        sys.exit()
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError) as e:
        print(e)
        _logger.error(e)
        print(f"Check logs/file.manager.log for additional information")
        sys.exit()

    print("File has been retired. File has been moved to .trash if "
          "stored internally")


def register_file(
    file_tracker: DatasetManager,
    source_file: Optional[str] = None,
    folder: Optional[str] = None,
    encoding: Optional[FileEncodingTypes] = None,
    metadata: Optional[bool] = None,
    tags: Optional[Union[str, list[str]]] = None,
    id: Optional[str] = None,
    use:Literal["test", "train", "validate", "other"] = "train"
):

    if source_file is None:
        source_file = str(get_user_input(
            user_prompt="Full path to the file to add",
            requested="str",
            helper="This is the full path to the file",
            allow_whitespace=False,
            min_characters=1
        ))
    file_w_path = source_file
    if not os.path.exists(file_w_path):
        print(f"File {file_w_path} not found")
        sys.exit(0)
    folder, filename = os.path.split(file_w_path)

    if encoding is None:
        encoding_str = str(get_user_input(
            user_prompt="Encoding",
            requested="str",
            choices=SUPPORTED_FILE_ENCODING_TYPES,
            helper="What encoding for the file."
        ))
        if encoding_str in SUPPORTED_FILE_ENCODING_TYPES:
            encoding = cast(FileEncodingTypes, encoding_str)
        else:
            raise ValueError("Failed to capture acceptable encoding")

    m_filename = None

    if metadata is None:
        # ask the question
        metadata = False
        meta_exists_input = str(get_user_input(
            user_prompt="Does a metadata file exist",
            requested="str",
            choices=["yes", "no"],
            helper="If no metadata file exists enter no, else yes"
        ))
        if meta_exists_input.lower() == "yes":
            metadata = True

    m_file_w_path = None
    if metadata:
        # There should be a metadata file
        file_ends = [".csv", ".pkl", ".json", ".txt", ".meta.json"]
        m_filename = filename
        for extension in file_ends:
            if filename.endswith(extension):
                m_filename = filename.removesuffix(extension)
        m_filename += ".meta.json"

        m_file_w_path = os.path.join(folder, m_filename)
        if not os.path.exists(m_file_w_path):
            print(f"WARNING: unable to find {m_file_w_path}. reverting to "
                  "NO for metadata file.")
            m_filename = None

    if id is not None and len(id) > 1:
        id = file_tracker.register(
            source_file=file_w_path,
            encoding=encoding,
            metadata_file=m_file_w_path,
            tags=tags,
            id=id,
            use=use
        )
    else:
        id = file_tracker.register(
            source_file=file_w_path,
            encoding=encoding,
            metadata_file=m_file_w_path,
            tags=tags,
            use=use
        )
    msg = f"Registered file as {id}"
    print(msg)
    _logger.info(msg)


def main():
    args = parse_args()

    # ensure the main folder is there
    os.makedirs(name=".tracking", exist_ok=True)

    ds_mgr = DatasetManager(folder=".tracking")

    if args.command == "report":
        ds_mgr.report(tag=args.tags)
    elif args.command == "register":
        register_file(
            file_tracker=ds_mgr,
            source_file=args.file,
            encoding=args.encoding,
            metadata=args.metadata,
            id=args.id,
            use=args.use
        )
    elif args.command == "find":
        if args.file is None:
            print(f"Filename is required to find an ID")
            sys.exit(1)

        id = ds_mgr.get_file_id(filename=args.file)
        print(f"ID for file is : {id}")
        sys.exit(0)

    elif args.command == "retire":
        if args.id is None:
            print(f"Filename is required to retire an ID")
            sys.exit(1)

        ds_mgr.retire_file(args.id)
    else:
        print(HELP_W_INTRO)
