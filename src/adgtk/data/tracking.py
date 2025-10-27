"""data.tracking.py is focused on providing a re-usable class based on
data usage needs. The overall goal of the data module to which the
tracking is the core is to provide a consistent and repeatable method
for letting agents know what files/data are available and for what
purpose.

Roadmap
=======
1. consider YAML and sqlite3 as additional file tracking solutions.
2. refactor report for better UI experience.
"""
import logging
import json
import os
from typing import Optional, Union
import uuid
from pydantic import ValidationError
from adgtk.data.structure import FileDefinition, FileEncodingTypes


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

class JsonFileTracker:
    """A simple file tracker that implements the CanTrackFiles protocol.
    It uses a json file the user defines to keep an inventory of files
    that can be used/referenced/loaded.
    """

    def __init__(
        self,
        label: str,
        inventory_file: str,
        logger: Optional[logging.Logger] = None
    ) -> None:
        self.label = label
        self.inventory_file = inventory_file
        self._inventory = {}
        self.logger = logger or logging.getLogger(__name__)        
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Loads the inventory from disk. If it doesn't exist it creates it
        in memory for a future save. The method expects JSON format.
        """
        if os.path.exists(self.inventory_file):
            with open(self.inventory_file, "r", encoding="utf-8") as infile:
                self._inventory = json.load(infile)

                for id, entry in self._inventory.items():
                    if not isinstance(entry, FileDefinition):
                        try:
                            entry = FileDefinition(**entry)
                            self._inventory[id] = entry
                        except ValidationError:
                            msg = ("Potential corruption when loading from "
                                   f"disk : with file {self.inventory_file}")
                            self.logger.error(msg)
                            raise Exception(msg)
                msg = (f"Loaded {len(self._inventory)} into "
                       "JsonFileTracker from disk")
                self.logger.info(msg)

        else:
            self.logger.warning(
                f"unable to load {self.inventory_file}. This is expected if "
                "creating a new tracker.")
            self._inventory = {}

    def _save_to_disk(self) -> None:
        """Saves the inventory to disk in JSON format."""
        with open(self.inventory_file, "w", encoding="utf-8") as outfile:
            out_data = {}
            for id, entry in self._inventory.items():
                if isinstance(entry, FileDefinition):
                    out_data[id] = entry.model_dump()
                else:
                    out_data[id] = entry
            json.dump(out_data, outfile, indent=2)
        self.logger.info(
            f"{self.label} saved inventory to {self.inventory_file}")

    def list_files(
        self,
        tag: Optional[Union[str, list]] = None
    ) -> list[FileDefinition]:
        """Provides a listing of files with the ability to filter based
        on tags.

        :param tag: The tag(s) to filter for, defaults to None
        :type tag: Optional[Union[str, list]], optional
        :raises ValueError: Corrupt inventory
        :return: A list of file definitions that match the query
        :rtype: list[FileDefinition]
        """

        found: list[FileDefinition] = []
        file: FileDefinition
        for _, file in self._inventory.items():
            # ensure consistent format
            if isinstance(file, FileDefinition):
                pass
            else:
                try:
                    file = FileDefinition(**file)
                except ValidationError:
                    raise ValueError("Corrupted inventory")
            # inspect each file. not fast but it works
            if tag is None:
                found.append(file)
            elif file.tags is not None:
                if isinstance(tag, list):
                    if all(entry in file.tags for entry in tag):
                        found.append(file)
                elif isinstance(tag, str):
                    if tag in file.tags:
                        found.append(file)
        return found
    
    def get_file_ids_only(
        self,
        tag: Optional[Union[str, list]] = None
    ) -> list[str]:
        files = self.list_files(tag=tag)
        return [file.file_id for file in files]


    def get_file_id(self, filename: str, path: Optional[str] = None) -> str:
        """Retrieves the file_id for the file requested.

        :param filename: The filename to search for
        :type filename: str
        :param path: The path override, defaults to None
        :type path: Optional[str], optional
        :raises ValueError: Corrupted inventory
        :raises FileNotFoundError: No file found for the filename
        :return: the file_id of the entry
        :rtype: str
        """

        file: FileDefinition
        for _, file in self._inventory.items():
            # ensure consistent format
            if isinstance(file, FileDefinition):
                pass
            else:
                try:
                    file = FileDefinition(**file)
                except ValidationError:
                    raise ValueError("Corrupted inventory")

            if file.filename == filename and file.path == path:
                return file.file_id

        raise FileNotFoundError()

    # TODO: refactor to provide better UI
    def report(self, tag: Optional[Union[str, list]] = None) -> None:
        """Generates a report and prints to console of all the files that
        are curently in the inventory.

        :param tag: The tag(s) to filter for, defaults to None
        :type tag: Optional[Union[str, list]], optional
        """

        longest = 0
        all_files = ""
        files = self.list_files(tag=tag)
        files.sort(key=lambda x: (x.path, x.filename))
        for file in files:
            path = file.path

            if file.tags is None:
                tags = ""
            else:
                tags = " ".join(file.tags)
            entry = (f" - {file.file_id:<35} | {file.filename:<30} | "
                     f"{path:<15} | {tags}")
            if len(entry) > longest:
                longest = len(entry)

            all_files += f"{entry}\n"

        # Setup title/'banner', the spaced out title for the columns
        title = f"{self.label} File Manager report"
        if tag is not None:
            if isinstance(tag, str) and len(tag) > 0:
                title = f"{self.label} File Manager report - tag: {tag}"
            elif isinstance(tag, list) and len(tag) > 0:
                tag_str = " ".join(tag)
                title = f"{self.label} File Manager report - tags: {tag_str}"

        filename = "Filename"
        path_str = "Folder"
        file_id_str = "File ID"
        banner = (f"    {file_id_str:<35} | {filename:<30} | "
                  f"{path_str:<15} | Tags")
        if len(title) > longest:
            longest = len(title)
        if len(banner) > longest:
            longest = len(banner)

        if longest > len(title):
            # now center the title
            spaces = int((longest-len(title))/2)
            space_str = " "*spaces
            title = f"\n{space_str}{title}"
        # and finally put everything together and print
        line = "="*longest
        small_line = "-"*longest
        title += f"\n{line}\n{banner}\n{small_line}\n{all_files}"
        print(title)

    def register_file(
        self,
        source_file: str,
        encoding: FileEncodingTypes,
        metadata_file: Optional[str] = None,
        tags: Optional[Union[str, list[str]]] = None,
        id: Optional[str] = None
    ) -> str:
        """Registers a file and if requested moves to internal data folder

        :param source_file: The name of the file w/path
        :type source_file: str
        :param encoding: The encoding of the file
        :type encoding: FileEncodingTypes
        :param tags: The tags for this file, defaults to None
        :type tags: Optional[list[str]], optional
        :param id: The requested ID, defaults to None
        :type id: Optional[str], optional
        :raises FileNotFoundError: File is not found
        :raises IndexError: The id already exists
        :return: The id of the file saved
        :rtype: str
        """

        # Do we need to move the file?
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"File must exist on disk: {source_file}.")

        # create an id if not already found
        if id is None:
            id = str(uuid.uuid4())

        # safety
        if id in self._inventory.keys():
            raise IndexError(f"ID: {id} already exists")

        # and prepare tags
        if tags is None:
            tags = []

        # Split into file and path
        dir, filename = os.path.split(source_file)

        # now create entry
        entry = FileDefinition(
            file_id=id,
            filename=filename,
            path=dir,
            encoding=encoding,
            metadata_file=metadata_file,
            tags=tags
        )

        self._inventory[id] = entry
        self._save_to_disk()
        self.logger.info(
            f"{self.label} created entry: {id} for file {source_file}")
        return id

    def retire_file(self, id: str) -> None:
        """Removes a file from the inventory. If the file is stored in the
        internal directory the file is moved to the .trash folder.

        :param id: The id of the file to retire
        :type id: str
        :raises IndexError: Unknown ID
        :raises InvalidConfiguration: Corrupted data
        :return: True if file retired
        :rtype: bool
        """
        if id not in self._inventory.keys():
            raise IndexError(f"Unknown ID: {id}")

        # now delete the entry
        del self._inventory[id]
        self.logger.info(
            f"{self.label} retired entry: {id}")
        self._save_to_disk()

    def get_file_definition(self, id: str) -> FileDefinition:
        """Retrieves the file definition for an ID.

        :param id: The id of the file
        :type id: str
        :raises KeyError: Unable to fine the file ID
        :return: The details associated with this file.
        :rtype: FileDefinition
        """

        if id in self._inventory.keys():
            return self._inventory[id].model_copy()

        msg = f"Unable to find file id {id}"
        raise KeyError(msg)

    def file_id_exists(self, id:str) -> bool:
        """An easy method to verify an id exists.

        :param id: The ID to check
        :type id: str
        :return: True if a valid ID in the system.
        :rtype: bool
        """

        if id in self._inventory.keys():
            return True
        return False