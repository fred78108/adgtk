"""Dataset management module.

Provides a consistent interface for registering, loading, and managing
datasets by inheriting from JsonFileTracker and utilizing file utilities.

Roadmap:
    1. Improved reporting by use.
"""

import os
from typing import Literal, Optional, Union
from adgtk.data.structure import FileEncodingTypes, PurposeTypes
from adgtk.data.tracking import JsonFileTracker
import adgtk.tracking.journal as exp_journal
from adgtk.data.utils import load_data_from_file, ReturnDataTypes
from adgtk.utils import create_logger


FILENAME = "datasets.json"


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
        metadata_file: Optional[str] = None,
        tags: Optional[Union[str, list[str]]] = None,
        id: Optional[str] = None,
        use: Literal["test", "train", "validate", "other"] = "other",
        purpose: PurposeTypes = "other"
    ) -> str:
        """Registers a file definition.

        Args:
            source_file: The name of the file with its path.
            encoding: The encoding of the file.
            metadata_file: Optional path to a metadata file. Defaults to None.
            tags: The tags for this file. Defaults to None.
            id: The requested ID. Defaults to None.
            use: Intended usage category (e.g., test, train).
                Defaults to "other".
            purpose: The purpose of the file for experiment tracking.
                Defaults to "other".

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
        exp_journal.add_file(filename=full_path, purpose=purpose)

        return self.register_file(
            source_file=full_path,
            encoding=encoding,
            metadata_file=metadata_file,
            tags=tags,
            id=id
        )

    def load_file(self, id: str) -> ReturnDataTypes:
        """Retrieves and loads data from a file using its tracker ID.

        Args:
            id: The unique identifier of the file in the tracker.

        Returns:
            The loaded data in its native or requested format.
        """
        file_def = self.get_file_definition(id)
        return load_data_from_file(file_def=file_def)
