"""The dataset module is focused on providing a consistent interface for
registering, loading, and managing datasets.  It accomplishes this by
inheriting the JsonFileTracker and using the file utilities provides an
easy to use interface for registering a file and loading the file by the
id.

Roadmap
=======
1. Improved reporting by use
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

    def __init__(
        self,
        name:str = "dataset.manager",
        folder: str = ".tracking",
        inventory_file: Optional[str] = None
    ) -> None:
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
        purpose:PurposeTypes= "other"
    ) -> str:
        """Registers a file definition.

        :param source_file: The name of the file w/path
        :type source_file: str
        :param encoding: The encoding of the file
        :type encoding: FileEncodingTypes
        :param tags: The tags for this file, defaults to None
        :type tags: Optional[list[str]], optional
        :param id: The requested ID, defaults to None
        :type id: Optional[str], optional
        :param purpose: The purpose of the file
        :type purpose: PurposeTypes
        :raises FileNotFoundError: File is not found
        :raises IndexError: The id already exists
        :return: The id of the file saved
        :rtype: str
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
        """Pulls the file definition from the file tracker and then uses
        the load_data_from_file utility function to load the data.

        :param id: the ID in the file_tracker.
        :type id: str
        :return: The loaded data
        :rtype: ReturnDataTypes
        """
        file_def = self.get_file_definition(id)
        return load_data_from_file(file_def=file_def)
