"""Built-in plotting utilities for ADGTK."""


from typing import Sequence
import matplotlib.pyplot as plt


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
