"""Managing multiple experiments via CSV using the experiment name as
the key.
"""

import os
import sys
import logging
import time
import csv
from numbers import Number
from typing import Literal, Union, List, Any
# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
#  CSV_DELIMETER = ","
# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------


class ExperimentSubmission:
    column_order: List[str] = ["name", "status", "date_started",
                               "date_completed", "short_description", "run_notes", "observations"]

    def __init__(
        self,
        name: str,
        status: Literal["completed", "canceled", "active", "pending"],
        date_started: Union[float, None] = None,
        date_completed: Union[float, None] = None,
        short_description: Union[str, None] = None,
        run_notes: Union[str, None] = None,
        observations: Union[str, None] = None
    ) -> None:
        if isinstance(name, Number):
            self.name = f"{name}"
        else:
            self.name = name

        self.status = status
        self.run_notes = run_notes
        self.short_description = short_description
        self.observations = observations

        # now generate if empty
        if date_started is None:
            self.date_started = time.time()
        else:
            self.date_started = date_started

        if date_completed is None:
            self.date_completed = time.time()
        else:
            self.date_completed = date_completed

    def get_row(self) -> List[Union[str, int, float, None]]:
        row: List[Union[str, int, float, None]] = []
        for key in self.column_order:
            # required fields
            if key == "name":
                row.append(self.name)
            elif key == "status":
                row.append(self.status)
            elif key == "date_started":
                row.append(self.date_started)
            elif key == "date_completed":
                row.append(self.date_completed)

            # and optional
            elif key == "short_description":
                if self.short_description is not None:
                    row.append(self.short_description)
                else:
                    row.append(" ")
            elif key == "run_notes":
                if self.run_notes is not None:
                    row.append(self.run_notes)
                else:
                    row.append(" ")
            elif key == "observations":
                if self.observations is not None:
                    row.append(self.observations)
                else:
                    row.append(" ")

        return row


# TODO: expand and introduce this class.
class ProjectJournal:
    """Provides a journal for a project. A project is one that extends
    over multiple experiments.
    """

    def __init__(
        self, results_dir: str = "results",
        data_file: str = "experiments.csv",
        overwrite_data_file_if_exists: bool = False
    ):
        self.experiments: dict[str, ExperimentSubmission] = {}
        self.results_dir = results_dir
        self.data_file = os.path.join(self.results_dir, data_file)
        if os.path.exists(self.data_file):
            self._load_data()
        else:
            self._create_file(force=overwrite_data_file_if_exists)

    def __len__(self) -> int:
        return len(self.experiments)

    def _load_data(self) -> None:
        columms: List[str] = []
        with open(self.data_file, "r", encoding="utf-8") as infile:
            csv_reader = csv.reader(infile)

            for row in csv_reader:
                if len(columms) == 0:
                    columms = row

                    # safety check. ensure consistent data.
                    for col in columms:
                        if col not in ExperimentSubmission.column_order:
                            raise KeyError(f"Unexpected column name: {col}")
                    # and the reverse
                    for col in ExperimentSubmission.column_order:
                        if col not in columms:
                            raise KeyError(f"Missing column name: {col}")

                else:
                    data: dict[str, Any] = {}
                    for col, entry in zip(columms, row):
                        data[col] = entry

                    # now create object
                    tmp_exp = ExperimentSubmission(**data)
                    if tmp_exp.name in self.experiments:
                        raise KeyError(
                            f"Duplicate experiment {tmp_exp.name} on load.")
                    self.experiments[tmp_exp.name] = tmp_exp

    def _create_file(self, force: bool = False) -> None:

        # safety check
        if os.path.exists(self.data_file) and not force:
            msg = "Attempted to overwrite the project data file."
            logging.warning(msg)
            sys.exit(os.EX_OSFILE)

        # create the folder if it doesn't exist
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir, exist_ok=True)

        # now the file
        with open(self.data_file, "w", encoding="utf-8") as outfile:
            writer = csv.writer(
                outfile, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(ExperimentSubmission.column_order)

    def _update_disk(self) -> None:
        with open(self.data_file, "w", encoding="utf-8") as outfile:
            writer = csv.writer(
                outfile, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(ExperimentSubmission.column_order)
            for _, item in self.experiments.items():
                writer.writerow(item.get_row())

    def add_entry(
        self,
        name: str,
        status: Literal["completed", "canceled", "active", "pending"],
        date_started: Union[float, None] = None,
        date_completed: Union[float, None] = None,
        short_description: Union[str, None] = None,
        run_notes: Union[str, None] = None,
        observations: Union[str, None] = None,
        overwrite_entry: bool = False
    ) -> None:
        if name in self.experiments and not overwrite_entry:
            logging.warning(f"Unable to add_entry. {name} already found.")
        else:
            self.experiments[name] = ExperimentSubmission(
                name=name,
                status=status,
                date_started=date_started,
                date_completed=date_completed,
                short_description=short_description,
                run_notes=run_notes,
                observations=observations)

        self._update_disk()

    def update_entry(
        self,
        name: str,
        status: Literal["completed", "canceled", "active", "pending"],
        date_started: Union[float, None] = None,
        date_completed: Union[float, None] = None,
        short_description: Union[str, None] = None,
        run_notes: Union[str, None] = None,
        observations: Union[str, None] = None
    ) -> None:
        if name not in self.experiments:
            raise KeyError(f"Experiment {name} not found")

        exp = self.experiments[name]
        if status is not None:
            exp.status = status

        if date_started is not None:
            exp.date_started = date_started

        if date_completed is not None:
            exp.date_completed = date_completed

        if short_description is not None:
            exp.short_description = short_description

        if run_notes is not None:
            exp.run_notes = run_notes

        if observations is not None:
            exp.observations = observations

        self._update_disk()

    def experiment_found(self, name: str) -> bool:
        return name in self.experiments
