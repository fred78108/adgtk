"""Record Structure

This module is focused on supporting the internal representation of
entity data. The design approach is to keep things consistent at the
core to ease measurements, etc. This greatly reduces the complexitiy
of parsing and ensuring consistency.

Versions:
v 0.1
- MVP
v 0.1.1
- added additional "help" for load_from_disk to add if needed the
  DATA_DIR.
v 0.1.2
 - bug fix: iteration now reset idx once the first iteration complete
v 0.2
 - added __str__ for entity pair
 - cleanup and added additional docstrings
 - expanded testing (so increasing v to 0.2)


References:
-

TODO:
- look for speedup, consider arrow (https://arrow.apache.org/), etc.
- consider reducing the pickle requirements (saving/loading). perhaps
  just the dict of the two entities along with some metadata?? a custom
  package perhaps i.e. a nested dict? keep things easier to port?
- improve performance of search with the home-grown vector Db search.
- test deepcopy functionality
- get consistent on presentation_config and where to apply here. Should
  with PairRecords and EntityRecords init with presenttion_config? The
  key will be saving/loading and the relationship with the data manager.
- remove __deepcopy__ from Entity and EntityPair.
- consider and test removing def copy() and use only __copy__ for all in
  this module that created a def copy.


Defects:
- doesn't impact accuracy but approach is slow and memory intensive
- defect with iterating w/filter for PairRecords

Test
python -m unittest tests.test_records
"""

# mypy: ignore-errors

__version__ = "0.2"
__author__ = "Fred Diehl"

from typing import Union
import random
import logging
import pickle
from copy import deepcopy
import pandas as pd
from datasets import Dataset
from utils.vector import Vectorizer, cosine_simularity
from utils.file import load_file_data
from utils.formatting import (
    yaml_string_to_dict,
    dict_to_yaml_string,
    cleanup_yaml_string,
    clean_yaml_string_then_validate)
from configs.experiment import DATA_DIR
from configs.formatting import (
    DEFAULT_FORMAT_CONFIG,
    LOG_UNABLE_TO_PROCESS_EXAMPLES,
    EMPTY_PLACEHOLDER,
    REPLACE_EMPTY_STRING_IN_DICT_WITH_PLACEHOLDER)
from configs.training import (
    EXPORT_RIGHT_SENTENCE_LABEL,
    EXPORT_LEFT_SENTENCE_LABEL,
    EXPORT_LABEL)
from constants.literals import DATA_FORMAT_LITERAL
from presentation.foundation import PresentationFormatConfig

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
MIN_FORMAT_STRING_LENGTH = 3
EXPAND_TO_DATA_DIR_IF_NEEDED = True
LOG_DATA_DIR_EXPANSION = True

TO_STRING_PAIR_INCLUDE_CR = True


# ----------------------------------------------------------------------
# Classes
# ----------------------------------------------------------------------

class Entity:
    """Represents a single entity. This is the internal data structure
    for managing the data itself as well as formatting a presentation
    of this data as defined by a PresentationFormatConfig.
    """

    def __init__(
        self,
        data: dict,
        presentation_config: PresentationFormatConfig = DEFAULT_FORMAT_CONFIG,
        string_rep: str = None,
        metadata: dict = None
    ) -> None:
        if not isinstance(data, dict):
            msg = f"data needs to be of type dict but got {type}"
            raise TypeError(msg)

        self._data = data
        self.string_rep = string_rep
        self.presentation_config = presentation_config  # for copy

        # and to make things easier to read in the code
        self.format = presentation_config.format
        self.replace_empty_placeholder = \
            presentation_config.replace_default_empty_placeholder
        self.replace_with = presentation_config.replace_default_with

        self.metadata = metadata
        self.build_string_rep()

    def __str__(self) -> str:
        """Uses the string_rep which is defined by the configured
        PresentationFormatConfig in order to return a string for use
        such as print statements.

        Returns:
            str: The string_rep of the Entity.
        """
        return self.string_rep

    def get_copy_of_data(self) -> dict:
        """Creates a copy of the data. This ensures that any use of the
        data is not directly accessed and inadvertently updated.

        Returns:
            dict: A copy of the internal data
        """
        return self._data.copy()

    def get_keys(self) -> list:
        """Returns the keys as a list for the internal data structure.

        Returns:
            list: the keys for the internal dict.
        """
        # extra cautious
        tmp_data = self.get_copy_of_data()
        return list(tmp_data.keys())

    def copy(self):
        """Creates a copy of an instance of an Entity.

        Returns:
            Entity: returns a copy of this entity.
        """
        return self.__copy__()

    def __copy__(self):
        return type(self)(
            self.get_copy_of_data(),
            self.presentation_config,
            self.string_rep,
            self.metadata)

    # TODO: reture this in a future cleanup
    def CANDIDATE_DELETE__deepcopy__(self, memo):
        """Candidate to delete. verify no usage before deleting."""
        id_self = id(self)
        _copy = memo.get(id_self)
        if _copy is None:
            _copy = type(self)(
                deepcopy(self._data, memo),
                deepcopy(self.format, memo),
                deepcopy(self.string_rep, memo),
                deepcopy(self.metadata, memo))
            memo[id_self] = _copy
        return _copy

    def build_string_rep(
        self,
        overwrite_config: PresentationFormatConfig = None
    ) -> None:
        """updates string_rep and returns string (to use inline)

        Args:
            impairments (list, optional): callable funcs that will
                impair a copy of the data before generating the string.
                Defaults to [].
            overwrite_config (PresentationFormatConfig): Overwrites the
                object settings. This can come in handy if a different
                format is needed such as multi-environment scenario.
                Defaults to None.

        Returns:
            None
        """
        if overwrite_config is None:
            if self.format == "yaml":
                self.string_rep = dict_to_yaml_string(self._data)
            if self.replace_empty_placeholder:
                self.string_rep = self.string_rep.replace(
                    EMPTY_PLACEHOLDER, self.replace_with)
        else:
            if overwrite_config.format == "yaml":
                self.string_rep = dict_to_yaml_string(self._data)
            if overwrite_config.replace_default_empty_placeholder:
                self.string_rep = self.string_rep.replace(
                    EMPTY_PLACEHOLDER, overwrite_config.replace_default_with)


class EntityPair:
    """Used for tracking and managing a pair of entities"""

    def __init__(
        self,
        left: Entity,
        right: Entity,
        label: Union[int, str, bool]
    ) -> None:
        self.left = left
        self.right = right
        self.label = label
        # Safety check
        if not isinstance(left, Entity):
            msg = f"Left not an Entity but type {type(left)}"
            raise TypeError(msg)
        if not isinstance(right, Entity):
            msg = f"right not an Entity but type {type(right)}"
            raise TypeError(msg)

        self.state = (
            self.left.string_rep,
            self.right.string_rep,
            self.label
        )
        self.int_label = None
        self._set_int_label()

    def __str__(self) -> str:
        """Used for converting this object into a string format for
        use such as printing.

        Returns:
            str: a single string with the data rep
        """
        left = str(self.left).rstrip()
        right = str(self.right).rstrip()

        if TO_STRING_PAIR_INCLUDE_CR:
            return f"EntityPair: \n  ..left..:\n{left}\n  ..right..:\n{right}\n"\
                f"  ..label..: {self.label}"

        return f"EntityPair: left={left} | right={right} | label={self.label}"

    def refresh_string_rep_and_state(
        self,
        overwrite_config: PresentationFormatConfig = None
    ) -> None:
        """Rebuilds the string representation for each entity based on
        either the already defined PresentationFormatConfig or the
        overwrite if its set.

        Args:
            overwrite_config (PresentationFormatConfig, optional): The
                format to use for the string representations as an
                overwrite from the already defined config.
                Defaults to None.
        """
        self.left.build_string_rep(overwrite_config)
        self.right.build_string_rep(overwrite_config)
        self.state = (
            self.left.string_rep,
            self.right.string_rep,
            self.label
        )

    def _set_int_label(self) -> None:
        """Sets the label to an int based on a fixed mapping.
        """
        # TOOD: consider making a transformation.
        if isinstance(self.label, int):
            self.int_label = self.label
        elif isinstance(self.label, str):
            if self.label.lower() == "false":
                self.int_label = 0
            elif self.label.lower() == "true":
                self.int_label = 1
            elif self.label.lower() == "match":
                self.int_label = 1
            elif self.label.lower() == "mismatch":
                self.int_label = 0
            elif isinstance(self.label, bool):
                # TODO: test this
                if self.label:
                    self.int_label = 1
                else:
                    self.int_label = 0
            else:
                logging.error("Invalid label type")

    def copy(self):
        """Creates a copy.

        Returns:
            EntityPair: Creates a copy of this instance
        """
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.left, self.right, self.label)

    def CANDIDATE_TO_REMOVE__deepcopy__(self, memo):
        """CANDIDATE TO REMOVE"""
        id_self = id(self)
        _copy = memo.get(id_self)
        if _copy is None:
            _copy = type(self)(
                deepcopy(self.left, memo),
                deepcopy(self.right, memo),
                deepcopy(self.label, memo))
            memo[id_self] = _copy
        return _copy


class PairRecords:
    """Used for managing and maintaining a set of EntityPairs.
    """

    def __init__(
        self,
        filter_max_string_length: float = None,
        presentation_config: PresentationFormatConfig = DEFAULT_FORMAT_CONFIG
    ) -> None:
        self.records = []
        self.idx = 0            # for iteration
        self.filter_max_string_length = filter_max_string_length
        self.presentation_config = presentation_config

    def reduce_to(self, upper_bound: int) -> None:
        """Reduces the number of records to the upper bound if the
        inherited class implements, else this is a no-op w/warning.

        Args:
            upper_bound (int): Drop until you reach this value
        """
        self.shuffle()
        self.records = self.records[:upper_bound]

    def shuffle(self) -> None:
        """Shuffles the order of records.
        """
        random.shuffle(self.records)

    def export_to_pandas(self) -> pd.DataFrame:
        """Exports the entities into a pandas dataframe

        Returns:
            pd.DataFrame: The resulting DataFrame
        """
        record_dict = self.export_to_dict()
        return pd.DataFrame.from_dict(data=record_dict, orient="columns")

    def export_to_dict(self) -> dict:
        """Exports the data into a dictionary.

        Returns:
            dict: The records in dict format.
        """
        left = []
        right = []
        label = []

        for record in self.records:
            left.append(record.left.get_copy_of_data())
            right.append(record.right.get_copy_of_data())
            label.append(record.label)

        return {
            "left": left,
            "right": right,
            "label": label
        }

    def import_from_dict(
        self,
        data: dict,
        metadata: dict = None
    ) -> bool:
        """Imports data from a dict and loads into the internal data
        structure.

        Args:
            data (dict): The source data
            metadata (dict, optional): Metadata for the record.
                Defaults to None.

        Raises:
            TypeError: Invalid type for importing from dict
            KeyError: Invalid data structure for dict to import

        Returns:
            bool: T: successful import.å
        """

        if metadata is None:
            metadata = {}

        before_load = len(self.records)

        # Safety checks.
        if not isinstance(data, dict):
            raise TypeError("Invalid type for importing from dict")
        if "left" not in data.keys():
            raise KeyError("Invalid data structure for dict to import")
        if "right" not in data.keys():
            raise KeyError("Invalid data structure for dict to import")
        if "label" not in data.keys():
            raise KeyError("Invalid data structure for dict to import")
        # if not isinstance(data['left'].data, dict):
        #    raise Exception("Invalid left data structure for dict to import")
        # if not isinstance(data['right'].data, dict):
        #    raise Exception("Invalid right data structure for dict to import")

        for record in data:
            left = Entity(
                data=record.left,
                presentation_config=self.presentation_config,
                metadata=metadata)
            right = Entity(
                data=record.right,
                presentation_config=self.presentation_config,
                metadata=metadata)
            self.records.add(
                left=left,
                right=right,
                label=record.label
            )
        after = len(self.records)
        expected = len(data.left)
        if (after - before_load) == expected:
            return True

        return False

    def rebuild_from_disk(self, filename: str) -> bool:
        """Rebuilds/Builds using a pickle file. It overwrites the
        records and the max length filter. Be sure to set back the max
        if using one.

        Args:
            filename (str): The filename to load

        Returns:
            bool: True/Loaded False/Error
        """
        self.records = load_file_data(
            filename=filename,
            data_type="pkl",
            folder_to_expand=DATA_DIR,
            expand_if_needed=True,
            log_errors=True)

        if len(self.records) > 0:
            return True

        return False

    def save_to_disk(self, filename: str) -> None:
        """Saves the records to disk using Pickle

        Args:
            filename (str): The filename with a path.
        """
        with open(filename, "wb") as outfile:
            pickle.dump(self.records, outfile)

    def __iter__(self):
        return self

    def __next__(self):
        if self.idx < len(self.records):
            self.idx += 1
            return self.records[(self.idx-1)]
        else:
            # reset for the next time we iterate
            self.idx = 0
            raise StopIteration

    # TODO: AA_ prefix to note skipping for now. See Bug
    def AA__next__(self):
        candidate = None
        while candidate is None:
            if self.idx < len(self.records):
                self.idx += 1
                candidate = self.records[(self.idx-1)]
            if self.filter_max_string_length is not None:
                # we need to test before we return
                left_len = len(candidate.left.string_rep)
                right_len = len(candidate.right.string_rep)
                if left_len > self.filter_max_string_length:
                    candidate = None
                if right_len > self.filter_max_string_length:
                    candidate = None
            else:
                raise StopIteration

        return candidate

    def __getitem__(self, index):
        return self.records[index]

    def __len__(self) -> int:
        return len(self.records)

    def add(self, pair: EntityPair):
        """Adds an EntityPair to the internal data structure.

        Args:
            pair (EntityPair): The record to add.

        Raises:
            TypeError: Invalid Type.
        """
        if isinstance(pair, EntityPair):
            self.records.append(pair)
        else:
            msg = f"Invalid Type: {type(pair)}"
            raise TypeError(msg)

    def get_all_records(self, copy: bool = False) -> list:
        """Retruns a list of all records.

        Args:
            copy (bool, optional): return a copy of the data?
                Defaults to False.

        Returns:
            list: a list of the records.
        """
        if copy:
            return self.records.copy()

        return self.records

    def clear_records(self) -> None:
        """Deletes all records from the internal data structure.
        """
        self.records = []

    def bulk_add(self, records: list) -> None:
        """Adds several records at once

        Args:
            records (list): A list of records to ad

        Raises:
            TypeError: Invalid type within the list.
        """
        for record in records:
            if not isinstance(record, EntityPair):
                raise TypeError("Expecting list of EntityPair")

        self.records += records

    def filter_by_label(
        self,
        label_filter: Union[int, bool, str],
        return_only_string: bool = True
    ) -> list:
        """Returns a filted list of the records

        Args:
            label_filter (Union[int, bool, str]): include only label of
            return_only_string (bool, optional): T: string_rep,
                F:EntityPair. Defaults to True.

        Returns:
            list: The filtered data
        """
        filtered_list = []
        for record in self.records:
            if record.label == label_filter:
                if return_only_string:
                    filtered_list.append(
                        (record.left.string_rep, record.right.string_rep)
                    )
                else:
                    filtered_list.append(record)
        return filtered_list

    def build_dict(self, max_length: int = None) -> dict:
        """considers both strings total length and skips adding to the
        resulting dict if too long. left.string_rep + right.string_rep

        Args:
            max_length (int, optional): total string length. Defaults to None.

        Returns:
            dict: collected data into a dict format
        """
        left_strings = []
        right_strings = []
        labels = []
        for record in self.records:
            # just in case/ensure latest string_rep
            record.refresh_string_rep_and_state()

            l, r, label = record.state
            if max_length is None:
                left_strings.append(l)
                right_strings.append(r)
                labels.append(label)
            else:
                left_len = len(l)
                right_len = len(r)
                if (left_len + right_len) < max_length:
                    left_strings.append(l)
                    right_strings.append(r)
                    labels.append(label)

        return {
            EXPORT_LEFT_SENTENCE_LABEL: left_strings,
            EXPORT_RIGHT_SENTENCE_LABEL: right_strings,
            EXPORT_LABEL: labels
        }

    def build_dataset(self, max_length: int = None) -> Dataset:
        """Builds a dataset using the internal records as the source.

        Args:
            max_length (int, optional): What is the maximum length of
                the source string? Defaults to None (no max)

        Returns:
            Dataset: A huggingface Dataset.
        """
        record_dict = self.build_dict(max_length=max_length)
        return Dataset.from_dict(record_dict)

    def set_format(self, new_format: PresentationFormatConfig) -> None:
        """Sets the format for the presentation of each entity and
        forces an update of the string_rep for each entity.

        Args:
            new_format (PresentationFormatConfig): The desired format.
        """
        msg = f"Setting format of records to {new_format.format}"
        logging.info(msg)
        for record in self.records:
            record.refresh_string_rep_and_state(new_format)


class EntityRecords:
    """Used for managing and tracking a set of Entities.
    """

    def __init__(
        self,
        build_vectors: bool = False,
        add_length_filter: int = None
    ) -> None:
        self.records = []
        self.idx = 0
        self.vectors = []
        self.vectorizer = Vectorizer()
        self.add_length_filter = add_length_filter
        self._build_vectors_flag = build_vectors

    def shuffle(self) -> None:
        """Shuffles the order of records.
        """
        random.shuffle(self.records)

    def reduce_to(self, upper_bound: int) -> None:
        """Reduces the number of records to the upper bound if the
        inherited class implements, else this is a no-op w/warning.

        Args:
            upper_bound (int): Drop until you reach this value
        """
        self.shuffle()
        self.records = self.records[:upper_bound]

    def search_by_cosine_similarity(
        self,
        entity: Union[str, Entity],
        similarity_min: float = 0,
        similarity_max: float = .99
    ) -> Union[Entity, None]:
        """MVP/Basic search

        Args:
            entity (Union[str, Entity]): The entity to compare against
            min (float, optional): Minimum distance. Defaults to 0
            max (float, optional): Maximum distance. Defaults to .99
        Raises:
            TypeError: Invalid type for searching
            LookupError: EntityRecords has no vectors built

        Returns:
            Union[Entity, None]: _description_
        """
        if not self._build_vectors_flag:
            raise LookupError("EntityRecords has no vectors built.")

        if isinstance(entity, Entity):
            search_string = entity.string_rep
        elif isinstance(entity, str):
            search_string = entity
        else:
            raise TypeError("Invalid type for searching")

        target = self.vectorizer.create_vector(search_string)
        best_vec_dist = -1000
        best_entity_idx = None
        for idx, vec in enumerate(self.vectors):
            cos = cosine_simularity(target, vec)
            if cos is not None:
                if best_entity_idx is None and cos > similarity_min \
                        and cos < similarity_max:
                    best_vec_dist = cos
                    best_entity_idx = idx
                elif cos > best_vec_dist and cos < similarity_max:
                    best_vec_dist = cos
                    best_entity_idx = idx

        if best_entity_idx is None:
            return None
        else:
            return self.records[best_entity_idx]

    def __iter__(self):
        return self

    def __next__(self):
        if self.idx < len(self.records):
            self.idx += 1
            return self.records[(self.idx-1)]
        else:
            # reset so we can iterate more than once
            self.idx = 0
            raise StopIteration

    def __getitem__(self, index):
        return self.records[index]

    def __len__(self) -> int:
        return len(self.records)

    def get_all_records(self, copy: bool = False) -> list:
        """Returns all records as a list.

        Args:
            copy (bool, optional): Return a copy of the records?
                Defaults to False.

        Returns:
            list: A list of the records
        """
        if copy:
            return self.records.copy()

        return self.records

    # odd bug here?
    def get_random_record(self) -> Entity:
        """Returns a random record.

        Returns:
            Entity: A single record from the internal data store.
        """
        return random.choice(self.records)

    def add(self, entity: Union[Entity, EntityPair]) -> None:
        """Adds an entity to the internal store

        Args:
            entity (Union[Entity, EntityPair]): The entity or entities
                to add. If passing a pair the function will split and
                add each side (left, right).

        Raises:
            TypeError: Invalid entity type
        """
        if isinstance(entity, EntityPair):
            # break out the two entities.
            self.add(entity.left)
            self.add(entity.right)
            return None

        elif not isinstance(entity, Entity):
            msg = f"Invalid entity type {type(entity)}"
            logging.fatal(msg)
            raise TypeError(msg)

        # loading the entitiy.
        inserted = False
        if self.add_length_filter is None:
            self.records.append(entity)
            inserted = True
        elif len(entity.string_rep) < self.add_length_filter:
            self.records.append(entity)
            inserted = True

        if self._build_vectors_flag and inserted:
            vec = self.vectorizer.create_vector(entity.string_rep)
            self.vectors.append(vec)

    def clear_records(self) -> None:
        """Clears the internal memory and resets to zero records.
        """
        self.records = []
        self.vectors = []

    def bulk_add(self, records: list) -> None:
        """Adds multiple entities at once.

        Args:
            records (list): A list of entities.
        """
        for record in records:
            self.add(record)

    def get_strings(self) -> list:
        """Get a list of the string_rep for each entity stored.

        Returns:
            list: a list of the string_rep of the entities.
        """
        string_records = []
        for record in self.records:
            string_records.append(record.string_rep)

        return string_records


# ----------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------

def determine_format_type(text: str) -> DATA_FORMAT_LITERAL:
    """Determines the format type. The primary usage of this is to help
    the agent read in and process the LLM output.

    Args:
        text (str): The string to inspect

    Returns:
        str: The likely type
    """
    # safety first!
    if len(text) < MIN_FORMAT_STRING_LENGTH:
        return "unknown"

    json_counter = 0
    valcol_counter = 0
    yaml_counter = 0
    if "{" in text:
        json_counter += 5
    else:
        json_counter -= 100
    if "}" in text:
        json_counter += 5
    else:
        json_counter -= 100
    if ":" in text:
        json_counter += 5
        yaml_counter += 20
    else:
        yaml_counter -= 100
        json_counter -= 100

    if "val" in text:
        valcol_counter += 5
    else:
        valcol_counter -= 100
    if "col" in text:
        valcol_counter += 5
    else:
        valcol_counter -= 100

    # check scores and return
    best_score = -500
    best_idx = -1
    for idx, counter in enumerate([json_counter, valcol_counter, yaml_counter]):
        if counter > best_score:
            best_idx = idx

    if best_idx == -1:
        # second attempt. bias to YAML right now.
        if clean_yaml_string_then_validate(text):
            return "yaml"
        # so its legit unknown
        return "unknown"
    if best_idx == 0:
        return "json"
    if best_idx == 1:
        return "valcol"
    if best_idx == 2:
        # this is the ideal pattern for the above. triple check.
        if clean_yaml_string_then_validate(text):
            return "yaml"

    # fall to unknown
    return "unknown"


def build_entity_from_unknown_type_string(
    text: str,
    presentation_config: PresentationFormatConfig = DEFAULT_FORMAT_CONFIG,
    metadata: dict = None,
    log_errors: bool = True
) -> Union[Entity, None]:
    """Attempts to build an Entity from a string when the format is not
    known. If it cannot determine the format then it returns None.

    Args:
        text (str): The source of the candidate entity.
        presentation_config (PresentationFormatConfig, optional): What
            format should the string_rep be in?Defaults to
                DEFAULT_FORMAT_CONFIG.
        metadata (dict, optional): Metadata for the entity.
            Defaults to None.
        log_errors (bool, optional): Log errors? Useful for validating
            and improving the funtion. Defaults to True.

    Returns:
        Union[Entity, None]: an Entity or None if unable to create.
    """
    format_type = determine_format_type(text)

    if format_type == "yaml":
        format_type = "yaml"
        # try going direct.
        data = yaml_string_to_dict(text)
        # unable to create w/out cleanup. try cleaning up
        if data is None:
            # cleanup needed?
            text = cleanup_yaml_string(text)
            data = yaml_string_to_dict(text)

            if data is None:
                # clean wasn't enough
                if LOG_UNABLE_TO_PROCESS_EXAMPLES or log_errors:
                    msg = f"Unable to build entity with string {text} "
                    logging.info(msg)
                return None
            elif not isinstance(data, dict):
                logging.error("Unexpected type returned by util func.")

    elif format_type == "unknown":
        return None
    elif format_type == "json":
        logging.warning("JSON transformation needs to re-write")
        return None
    elif format_type == "valcol":
        logging.warning("VALCOL transformation needs to re-write")
        return None
    else:
        logging.warning("Unexpected type identified.")
        return None

    if not isinstance(data, dict):
        # msg = f"Invalid Type post processing: {type(data)} | {data}"
        msg = f"Invalid Type post processing: {type(data)} | {data}"
        print(f"{format_type} :: {msg}")
        logging.error(msg)
        return None

    # only make it here when data exists
    if REPLACE_EMPTY_STRING_IN_DICT_WITH_PLACEHOLDER:
        for key, value in data.items():
            if value == "''" or value == '""':
                data[key] = EMPTY_PLACEHOLDER

    # We have a good type and its cleaned up as needed.
    return Entity(
        data=data,
        metadata=metadata,
        presentation_config=presentation_config)
