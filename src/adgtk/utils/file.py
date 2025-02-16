"""File processing utilities.
"""

from typing import Any
import csv

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#  CSV
# ----------------------------------------------------------------------


def load_data_from_csv_file(filename:str) -> list:
      """Loads a CSV file into a list of dictionaries.

      :param filename: The name of the file to load
      :type filename: str
      :return: The data from the file
      :rtype: list
      """
      columns: list[str] = []
      records: list[dict] = []

      with open(filename, "r") as infile:
            csv_reader = csv.reader(infile)
            for row in csv_reader:
                  # we are on the first row when len == 0
                  if len(columns) == 0:
                        columns = row
                  else:
                        data: dict[Any, Any] = {}
                        for idx, col in enumerate(columns):
                              data[col] = row[idx]
                              records.append(data)
      return records
