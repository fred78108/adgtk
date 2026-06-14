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
        """Initializes the JsonFileTracker.

        Args:
            label: A label for the tracker instance (used in logging).
            inventory_file: The file path to the JSON inventory.
            logger: An optional logger instance. Defaults to a
                module-level logger.
        """
        self.label = label
        self.inventory_file = inventory_file
        self._inventory: dict[str, FileDefinition] = {}
        self.logger = logger or logging.getLogger(__name__)
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Loads the inventory from disk.

        If the inventory file does not exist, an empty inventory is
        initialized. The method expects the file to be in JSON format and
        validates entries against the FileDefinition schema.
        """
        if os.path.exists(self.inventory_file):
            with open(self.inventory_file, "r", encoding="utf-8") as infile:
                self._inventory = json.load(infile)

                for file_id, entry in self._inventory.items():
                    if not isinstance(entry, FileDefinition):
                        try:
                            entry = FileDefinition(**entry)
                            self._inventory[file_id] = entry
                        except ValidationError:
                            msg = ("Potential corruption when loading from "
                                   f"disk : with file {self.inventory_file}")
                            self.logger.error(msg)
                            raise Exception(msg)
                msg = (f"Loaded {len(self._inventory)} into "
                       "JsonFileTracker from disk")
                self.logger.debug(msg)

        else:
            self.logger.warning(
                f"unable to load {self.inventory_file}. This is expected if "
                "creating a new tracker.")
            self._inventory = {}

    def _save_to_disk(self) -> None:
        """Saves the current inventory state to disk in JSON format.

        Serializes FileDefinition objects using model_dump before writing.
        """
        with open(self.inventory_file, "w", encoding="utf-8") as outfile:
            out_data = {}
            for file_id, entry in self._inventory.items():
                if isinstance(entry, FileDefinition):
                    out_data[file_id] = entry.model_dump()
                else:
                    out_data[file_id] = entry
            json.dump(out_data, outfile, indent=2)
        self.logger.info(
            f"{self.label} saved inventory to {self.inventory_file}")

    def list_files(
        self,
        tag: Optional[Union[str, list]] = None
    ) -> list[FileDefinition]:
        """Lists files in the inventory, optionally filtered by tags.

        Args:
            tag: A single tag or a list of tags to filter for. All provided
                tags must be present on the file for it to be included.
                Defaults to None.

        Returns:
            A list of FileDefinition objects matching the filter criteria.
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
        """Retrieves only the file IDs from the inventory, optionally
        filtered by tags.

        Args:
            tag: Tag or list of tags to filter by. Defaults to None.

        Returns:
            A list of strings representing the file IDs.
        """
        files = self.list_files(tag=tag)
        return [file.file_id for file in files]

    def get_file_id(self, filename: str, path: Optional[str] = None) -> str:
        """Retrieves the file ID for a specific filename and path.

        Args:
            filename: The name of the file to search for.
            path: The path associated with the file. Defaults to None.

        Returns:
            The file_id of the matching entry.

        Raises:
            ValueError: If the inventory is found to be corrupted.
            FileNotFoundError: If no entry matches the filename and path.
        """
        file: FileDefinition
        for _, file in self._inventory.items():
            # ensure consistent format
            if not isinstance(file, FileDefinition):
                file = FileDefinition(**file)

            if file.filename == filename and file.path == path:
                return file.file_id

        raise FileNotFoundError()

    # TODO: refactor to provide better UI
    def report(self, tag: Optional[Union[str, list]] = None) -> None:
        """Generates and prints a formatted report of files in the inventory.

        Args:
            tag: Optional tag or list of tags to filter the report.
                Defaults to None.
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
        tags: Optional[Union[str, list[str]]] = None,
        file_id: Optional[str] = None,
        description: Optional[str] = None,
        extended_metadata: Optional[dict] = None,
    ) -> str:
        """Registers a file in the tracker inventory.

        Args:
            source_file: The absolute or relative path to the file.
            encoding: The encoding/format type of the file.
            tags: Optional tags to categorize the file. Defaults to None.
            file_id: Optional explicit ID. If None, a UUID is generated.
            description: Optional human-readable description.
            extended_metadata: Optional dict of custom fields.

        Returns:
            The ID assigned to the registered file.

        Raises:
            FileNotFoundError: If the source_file does not exist on disk.
            IndexError: If the provided ID already exists in the inventory.
        """
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"File must exist on disk: {source_file}.")

        if file_id is None:
            file_id = str(uuid.uuid4())

        if file_id in self._inventory.keys():
            raise IndexError(f"ID: {file_id} already exists")

        if tags is None:
            tags = []

        dir, filename = os.path.split(source_file)

        entry = FileDefinition(
            file_id=file_id,
            filename=filename,
            path=dir,
            encoding=encoding,
            tags=tags,
            description=description,
            extended_metadata=extended_metadata,
        )

        self._inventory[file_id] = entry
        self._save_to_disk()
        self.logger.info(
            f"{self.label} created entry: {file_id} for file {source_file}")
        return file_id

    def retire_file(self, file_id: str) -> None:
        """Removes a file entry from the inventory.

        Args:
            file_id: The ID of the file to retire.

        Raises:
            IndexError: If the ID is not found in the inventory.
        """
        if file_id not in self._inventory.keys():
            raise IndexError(f"Unknown ID: {file_id}")

        # now delete the entry
        del self._inventory[file_id]
        self.logger.info(
            f"{self.label} retired entry: {file_id}")
        self._save_to_disk()

    def get_file_definition(self, file_id: str) -> FileDefinition:
        """Retrieves the file definition for a given ID.

        Args:
            file_id: The ID of the file.

        Returns:
            A copy of the FileDefinition associated with the ID.

        Raises:
            KeyError: If the file ID is not found.
        """
        if file_id in self._inventory.keys():
            return self._inventory[file_id].model_copy()

        msg = f"Unable to find file id {file_id}"
        raise KeyError(msg)

    def update_file(
        self,
        file_id: str,
        new_id: Optional[str] = None,
        new_tags: Optional[list] = None,
        new_description: Optional[str] = None,
        new_extended_metadata: Optional[dict] = None,
    ) -> str:
        """Updates a file entry's fields.

        Args:
            file_id: The current ID of the file entry.
            new_id: Optional new ID. If provided and different, renames the
                entry.
            new_tags: Optional replacement tag list.
            new_description: Optional replacement description.
            new_extended_metadata: Optional replacement extended metadata dict.

        Returns:
            The (potentially new) ID of the updated entry.

        Raises:
            KeyError: If the current ID is not found.
            IndexError: If new_id already exists in the inventory.
        """
        source_id = file_id
        if file_id not in self._inventory:
            raise KeyError(f"Unknown ID: {file_id}")
        entry = self._inventory[file_id].model_copy()

        if new_tags is not None:
            entry.tags = new_tags
        if new_description is not None:
            entry.description = new_description
        if new_extended_metadata is not None:
            entry.extended_metadata = new_extended_metadata

        if new_id is not None and new_id != file_id:
            if new_id in self._inventory:
                raise IndexError(f"ID '{new_id}' already exists")
            entry.file_id = new_id
            del self._inventory[file_id]
            self._inventory[new_id] = entry
            self._save_to_disk()
            return new_id

        self._inventory[file_id] = entry
        self._save_to_disk()
        if new_id is not None:
            if new_id != source_id:
                self.logger.info("Changed id from %s to %s", source_id, new_id)
        return file_id

    def file_id_exists(self, file_id: str) -> bool:
        """Verifies if a specific ID exists in the inventory.

        Args:
            file_id: The ID to check.

        Returns:
            True if the ID exists in the system, False otherwise.
        """
        if file_id in self._inventory.keys():
            return True
        return False
