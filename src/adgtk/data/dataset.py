"""Dataset management module.

Provides a consistent interface for registering, loading, and managing
datasets by inheriting from JsonFileTracker and utilizing file utilities.

Roadmap:
    1. Improved reporting by use.
"""

import os
from pathlib import Path
from typing import Literal, Optional, Union
from adgtk.data.structure import FileEncodingTypes
from adgtk.tracking.dataset import JsonFileTracker
from adgtk.data.utils import load_data_from_file, ReturnDataTypes
from adgtk.utils import create_logger


FILENAME = "datasets.json"


def find_blueprints_using_dataset(
    dataset_id: str,
    blueprints_dir: str = "blueprints",
) -> list[str]:
    """Return blueprint names that reference the given dataset ID.

    Scans all *.yaml files in blueprints_dir for an exact string match of
    dataset_id. Returns a sorted list of blueprint name stems (no extension).
    """
    bp_dir = Path(blueprints_dir)
    if not bp_dir.is_dir():
        return []
    names = []
    for path in bp_dir.glob("*.yaml"):
        try:
            if dataset_id in path.read_text(encoding="utf-8"):
                names.append(path.stem)
        except OSError:
            continue
    return sorted(names)


class DatasetManager(JsonFileTracker):
    """Manages dataset registration and loading using a JSON-based inventory.

    Inherits from JsonFileTracker to provide tracking and persistence for
    dataset files.
    """

    def __init__(
        self,
        name: str = "dataset.manager",
        folder: str = ".tracking",
        inventory_file: Optional[str] = None
    ) -> None:
        """Initializes the DatasetManager.

        Args:
            name: The name used for the tracker label and logging.
                Defaults to "dataset.manager".
            folder: The directory where tracking files are stored.
                Defaults to ".tracking".
            inventory_file: Custom filename for the inventory.
                Defaults to None.
        """
        os.makedirs(folder, exist_ok=True)
        file_name = inventory_file or FILENAME
        file_w_path = os.path.join(folder, file_name)
        self.logger = create_logger(
            logfile=f"{name}.log",
            logger_name=name,
            subdir="common"
        )
        super().__init__(
            label=name,
            inventory_file=file_w_path,
            logger=self.logger
        )

    def register(
        self,
        source_file: str,
        encoding: FileEncodingTypes,
        tags: Optional[Union[str, list[str]]] = None,
        file_id: Optional[str] = None,
        use: Literal["test", "train", "validate", "other"] = "other",
        description: Optional[str] = None,
        extended_metadata: Optional[dict] = None,
    ) -> str:
        """Registers a file definition.

        Args:
            source_file: The name of the file with its path.
            encoding: The encoding of the file.
            tags: The tags for this file. Defaults to None.
            file_id: The requested ID. Defaults to None.
            use: Intended usage category appended as a tag (test, train,
                validate, other). Defaults to "other".
            description: Optional human-readable description.
            extended_metadata: Optional dict of custom fields.

        Raises:
            FileNotFoundError: If the source file is not found on disk.
            IndexError: If the provided ID already exists in the inventory.

        Returns:
            The unique ID assigned to the registered file.
        """
        full_path = os.path.abspath(source_file)
        if not os.path.exists(full_path):
            raise FileNotFoundError("unable to find file: %s", full_path)

        if tags is None:
            tags = []
        elif isinstance(tags, str):
            tags = [tags]
        tags.append(use)

        return self.register_file(
            source_file=full_path,
            encoding=encoding,
            tags=tags,
            file_id=file_id,
            description=description,
            extended_metadata=extended_metadata,
        )

    def report(self, tag=None) -> None:
        """Print inventory report with blueprint usage counts."""
        files = self.list_files(tag=tag)
        files.sort(key=lambda x: (x.path, x.filename))

        title = f"{self.label} File Manager report"
        if tag:
            tag_str = tag if isinstance(tag, str) else " ".join(tag)
            if tag_str:
                title = f"{self.label} File Manager report - tags: {tag_str}"

        cid, cfile, cpath, ctags, cused = 35, 30, 15, 20, 6
        header = (
            f"    {'File ID':<{cid}} | {'Filename':<{cfile}} | "
            f"{'Folder':<{cpath}} | {'Tags':<{ctags}} | {'Used':>{cused}}"
        )

        rows = []
        for file in files:
            file_tags = " ".join(file.tags) if file.tags else ""
            bp_count = len(find_blueprints_using_dataset(file.file_id))
            used = str(bp_count) if bp_count else "-"
            rows.append(
                f" - {file.file_id:<{cid}} | {file.filename:<{cfile}} | "
                f"{file.path:<{cpath}} | {file_tags:<{ctags}}"
                f" | {used:>{cused}}"
            )

        all_lines = [title, header] + rows
        longest = max((len(s) for s in all_lines), default=len(title))
        line = "=" * longest
        small_line = "-" * longest
        spaces = " " * max(0, (longest - len(title)) // 2)
        print(f"\n{spaces}{title}\n{line}\n{header}\n{small_line}")
        for row in rows:
            print(row)

    def load_file(self, file_id: str) -> ReturnDataTypes:
        """Retrieves and loads data from a file using its tracker ID.

        Args:
            file_id: The unique identifier of the file in the tracker.

        Returns:
            The loaded data in its native or requested format.
        """
        file_def = self.get_file_definition(file_id)
        return load_data_from_file(file_def=file_def)
