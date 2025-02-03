"""Visuals for data. These functions seek to create very extensible and
flexible tools for use by journals and Agents."""

import logging
from typing import Iterable, Sequence
from numbers import Number
from typing import Union
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_presentation.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

PLT_LENGTH_RATIO = 3.6
PLT_HEIGHT = 10

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------


def plot_count_value_by_key(
    df: pd.DataFrame,
    title: str = "value count by key",
    save_as: Union[str, None] = None,
    filter_on_keys: Union[list, None] = None
):
    """Plots the count of values by key

    :param df: The dataframe to process
    :type df: pd.DataFrame
    :param title: The plot title, defaults to "value count by key"
    :type title: str, optional
    :param save_as: The filename, defaults to None
    :type save_as: Union[str, None], optional
    :param filter_on_keys: restrict plot to the keys, defaults to None
    :type filter_on_keys: Union[list, None], optional
    """
    # process the data
    if filter_on_keys is not None:
        df = df[filter_on_keys]

    nan_counts = df.notna().sum()
    nan_counts = nan_counts.sort_values()
    tmp_df = nan_counts.to_frame().T
    labels = list(tmp_df.keys())
    values = list(tmp_df.values[0])

    # plot the data
    fig, ax = plt.subplots()
    ax.barh(y=labels, width=values)
    ax.set_title(title)
    ax.set_xlabel("Records with a value")
    ax.set_ylabel("Key")
    if save_as is not None:
        fig.savefig(fname=save_as, bbox_inches="tight")


def plot_count_nan_by_key(
    df: pd.DataFrame,
    title: str = "NaN count by key",
    save_as: Union[str, None] = None,
    filter_on_keys: Union[list, None] = None
):
    # process the data
    if filter_on_keys is not None:
        df = df[filter_on_keys]

    nan_counts = df.isna().sum()
    nan_counts = nan_counts.sort_values()
    tmp_df = nan_counts.to_frame().T
    labels = list(tmp_df.keys())
    values = list(tmp_df.values[0])

    # plot the data
    fig, ax = plt.subplots()
    ax.barh(y=labels, width=values)
    ax.set_title(title)
    ax.set_xlabel("Records missing the key")
    ax.set_ylabel("Key")
    if save_as is not None:
        fig.savefig(fname=save_as, bbox_inches="tight")


def multi_line_data_validation(data: Sequence[Sequence]) -> bool:
    """Verifies data prior to plotting attempt.

    :param data: The data to validate
    :type data: Sequence[Sequence]
    :return: True: valid date, else False
    :rtype: bool
    """
    if not isinstance(data, Iterable):
        return False

    if len(data) == 0:
        return False

    if not isinstance(data[0], Iterable):
        return False

    if len(data[0]) == 0:
        return False

    if not isinstance(data[0][0], Number):
        return False

    return True


def plot_single_line(
    data: Sequence,
    filename: str,
    data_label: str = "",
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    show_legend: bool = False
) -> bool:
    """Plots a single line. basic plotting only

    :param data: the data to plot on th Y axis
    :type data: Sequence
    :param filename: the filename to save the image to
    :type filename: str
    :param data_label: if using a legend what is the data label,
        defaults to ""
    :type data_label: str, optional
    :param title: Title for the plot, defaults to ""
    :type title: str, optional
    :param x_label: label for the X-axis, defaults to ""
    :type x_label: str, optional
    :param y_label: label for the Y-axis, defaults to ""
    :type y_label: str, optional
    :param show_legend: show the legend?, defaults to False
    :type show_legend: bool, optional
    :return: True if plot attempted.
    :rtype: bool
    """

    x = range(len(data))
    if len(x) == 0:
        return False

    plt.plot(x, data, label=data_label)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    if show_legend:
        plt.legend()
    plt.savefig(filename)
    return True


def plot_multiple_lines(
    data: Sequence,
    labels: Sequence[Sequence],
    data_label: str = "value",
    filename: Union[str, None] = None,
    title: Union[str, None] = None,
    x_label: Union[str, None] = None,
    y_label: Union[str, None] = None,
    show_legend: bool = False
) -> matplotlib.figure.Figure:
    """Generates a line plot for a dynamic number of rows of data

    :param data: a Sequence of Sequence
    :type data: Sequence[Sequence]
    :param labels: The labels for each data series
    :type labels: Sequence
    :param data_label: The data for the legend, defaults to "value"
    :type data_label: str, optional
    :param filename: If saving, filename w/path, defaults to None
    :type filename: Union[str, None], optional
    :param title: The title of the plot, defaults to None
    :type title: Union[str, None], optional
    :param x_label: The label for the X-axis, defaults to None
    :type x_label: Union[str, None], optional
    :param y_label: The label for the Y-axis, defaults to None
    :type y_label: Union[str, None], optional
    :param show_legend: Show the legend?, defaults to False
    :type show_legend: bool, optional
    :rtype: matplotlib.figure.Figure
    """
    if not multi_line_data_validation(data):
        logging.warning("Invalid data format. No plot created.")

    if len(data) != len(labels):
        logging.warning("Labels don't match data. bypassing labels")
        labels = []
        for x in range(len(data)):
            labels.append(f"data-{x}")

    num_rows = len(data)

    length = num_rows * PLT_LENGTH_RATIO
    fig, axs = plt.subplots(
        num_rows, 1, figsize=(PLT_HEIGHT, length), layout="constrained")
    for idx, vals in enumerate(data):
        axs[idx].plot(vals, label=data_label)
        axs[idx].set_title(labels[idx], fontsize=14, loc="left")
        if x_label is not None:
            axs[idx].set_xlabel(x_label)
        if y_label is not None:
            axs[idx].set_ylabel(y_label)

        if show_legend:
            axs[idx].legend()

    if title is not None:
        fig.suptitle(title, fontsize=18)

    if filename is not None:
        with open(filename, "wb") as outfile:
            plt.savefig(outfile, format="png")

    return fig
