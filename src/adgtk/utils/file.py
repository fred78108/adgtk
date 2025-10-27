"""File processing utilities.
"""


import csv
import os
import shutil
from typing import Any

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



def clear_folder(folder_path: str) -> None:
    """Clears all files and subfolders in the given folder.

    :param folder_path: Path to the folder to clear
    :type folder_path: str

    raises:
        FileNotFoundError: when the folder does not exist
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError("The folder '%s' does not exist.", folder_path)
    
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
