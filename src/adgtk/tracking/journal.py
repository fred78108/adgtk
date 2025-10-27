"""journal.py is intended as the common journal for the experiment."""

import json
import os
from typing import Optional
import datetime
from adgtk.data.structure import FileEntry, PurposeTypes
from adgtk.tracking.structure import CommentModel


# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------

# data
_files_written: list[FileEntry] = []
_comments:list[CommentModel] = []

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def _get_components() ->set[str]:
    """Obtains a listing (via a set) of the components recorded.

    :return: A set of the components within the comments
    :rtype: set[str]
    """
    found = []
    for entry in _comments:
        found.append(entry.component)

    return set(found)


# ----------------------------------------------------------------------
# Public Functions
# ----------------------------------------------------------------------

def reset() -> None:
    """Resets the journal tracking. primary purpose would be when doing
    batch processing and you have multiple scenarios.
    """
    global _files_written
    global _comments
    _files_written = []
    _comments = []


def add_file(filename:str, purpose:PurposeTypes) -> None:
    """Writes a file save to the journal

    Args:
        filename (str): _description_
        purpose (PurposeTypes): _description_
    """
    file = FileEntry(filename=filename, purpose=purpose)
    if file not in _files_written:
        _files_written.append(file)

def add_comment(
    comment:str,
    use_timestamp:bool=True,
    component:Optional[str]=None
) -> None:
    """Adds a comment to the journal

    :param comment: The comment to add
    :type comment: str
    :param use_timestamp: include timestamp in the statement, defaults to True
    :type use_timestamp: bool, optional
    :param component: a component tag, defaults to None
    :type component: Optional[str], optional
    """
    now = None
    if use_timestamp:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if component is None:
        entry = CommentModel(comment=comment, timestamp=now)
    else:
        entry = CommentModel(
            comment=comment, timestamp=now, component=component)

    if entry not in _comments:
        _comments.append(entry)


def save_journal(path:str, filename:str="journal.json") -> None:
    """Saves the journal to disk as a json file.

    :param path: the path for where to write
    :type path: str
    :param filename: The filename to use, defaults to "journal.json"
    :type filename: str, optional
    """

    file_w_path = os.path.join(path, filename)
    comments_as_dicts = [comment.model_dump() for comment in _comments]
    files_as_dicts = [file.model_dump() for file in _files_written]
    data = {
        "comments": comments_as_dicts,
        "files": files_as_dicts
    }
    # Now write to JSON
    with open(file=file_w_path, mode='w', encoding="utf-8") as outfile:
        json.dump(files_as_dicts, outfile, indent=2)

def generate_report(
    path:str,
    experiment_name:str,
    filename:str="report.html"
) -> None:
    """Generates a report. This is more a human readable version. The
    save_journal and its json is the truly the target for an Agent to
    use for review of the experiment.

    :param path: The path on where to write the report
    :type path: str
    :param The name of the experiment: _description_
    :type experiment_name: str
    :param filename: The filename to use, defaults to "report.html"
    :type filename: str, optional
    """
    components = _get_components()


    # old code from previous design    

    # template = env.get_template("report.jinja")
    # try:
    #     output = template.render(
    #         date_ran=date_ran,
    #         experiment_name=experiment_name,
    #         comments=self._comments,
    #         tools=tools,
    #         measurement_section=measurement_html,
    #         scenario_def=self._scenario_def,
    #         data_section=data_html)
    #     with open(
    #             file=report_filename,
    #             encoding="utf-8",
    #             mode="w") as outfile:
    #         outfile.write(output)
    # except jinja2.exceptions.TemplateSyntaxError as e:
    #     logging.error("Syntax error with report.jinja")
