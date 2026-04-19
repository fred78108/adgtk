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
_comments: list[CommentModel] = []

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _get_components() -> set[str]:
    """Obtains a listing of the unique components recorded in comments.

    Returns:
        set[str]: A set of component names found in the comments.
    """
    found = []
    for entry in _comments:
        found.append(entry.component)

    return set(found)


# ----------------------------------------------------------------------
# Public Functions
# ----------------------------------------------------------------------

def reset() -> None:
    """Resets the journal tracking.

    The primary purpose is for batch processing where multiple scenarios
    are executed.
    """
    global _files_written
    global _comments
    _files_written = []
    _comments = []


def add_file(filename: str, purpose: PurposeTypes) -> None:
    """Records a file entry in the journal.

    Args:
        filename (str): The name of the file to record.
        purpose (PurposeTypes): The intended purpose of the file.
    """
    file = FileEntry(filename=filename, purpose=purpose)
    if file not in _files_written:
        _files_written.append(file)


def add_comment(
    comment: str,
    use_timestamp: bool = True,
    component: Optional[str] = None
) -> None:
    """Adds a comment to the journal.

    Args:
        comment (str): The comment string to add.
        use_timestamp (bool, optional): Whether to include a timestamp.
            Defaults to True.
        component (str, optional): An optional component tag for the
            comment. Defaults to None.
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


def save_journal(path: str, filename: str = "journal.json") -> None:
    """Saves the journal to disk as a JSON file.

    Args:
        path (str): The directory path where the journal will be saved.
        filename (str, optional): The filename for the journal.
            Defaults to "journal.json".
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
        json.dump(data, outfile, indent=2)


def generate_report(
    path: str,
    experiment_name: str,
    filename: str = "report.html"
) -> None:
    """Generates a human-readable report of the journal.

    The primary target for agent review is the JSON output from
    save_journal.

    Args:
        path (str): The directory path where the report will be written.
        experiment_name (str): The name of the experiment.
        filename (str, optional): The filename for the report.
            Defaults to "report.html".
    """
    pass
    # components = _get_components()
    # TODO: need to refactor and introduce back

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
