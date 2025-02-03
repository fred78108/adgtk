"""Comparison measurements
"""


from typing import Union
from numbers import Number
from adgtk.components.data import PresentableRecord, PresentableGroup
import adgtk.common.css as css
from adgtk.common import FactoryBlueprint, ArgumentSetting, ArgumentType
from adgtk.instrumentation import (
    MeasInputType,
    MeasOutputType,
    MeasurementFeatures,)

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/instrumentation/test_comparisons.py


def calc_overlap(a: list[str], b: list[str]) -> float:
    """Calculates the overlap measure between two lists. This function
    is more a common calculation across multiple comparison Measurements

    :param a: first list
    :type a: list[str]
    :param b: second list
    :type b: list[str]
    :return: overlap calculation
    :rtype: float
    """
    a_filtered_set = set(a)
    b_filtered_set = set(b)
    intersection_set = a_filtered_set.intersection(b_filtered_set)
    longest = max(len(a_filtered_set), len(b_filtered_set))
    return len(intersection_set) / longest


# -----------------------------------------------------------------
# Word Overlap
# -----------------------------------------------------------------

class WordOverlap:
    """WordOverlap is my implementation of the word overlap
        mesaurement as defined in ZeroShotDataAug with some
        modifications. This method has the option to not remove
        stop-words. The primary purpose is when we want to compare keys.
        An assumption made here is that the longer text is post removal
        of the stop words (max) used to divide. The paper is not clear
        on this."""

    description = "Measures word overlap between two strings"
    # for blueprint factory use
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "word-overlap",
        "arguments": {
            "tracker_label": ArgumentSetting(
                help_str="The label for a metric tracker",
                default_value="word-overlap",
                argument_type=ArgumentType.STRING),
            "use_stopwords": ArgumentSetting(
                help_str="Use stop-words",
                default_value=False,
                argument_type=ArgumentType.BOOL)
        }
    }
    features = MeasurementFeatures(
        count_min=None,
        count_max=None,
        input_type=[MeasInputType.PRESENTABLE_RECORD, MeasInputType.STRING],
        output_type=MeasOutputType.FLOAT,
        can_use_stopwords=True)

    def __init__(
        self,
        use_stopwords: bool = False,
        tracker_label: str = "word-overlap"
    ):
        self.stopwords: list[str] = []
        self.use_stopwords = use_stopwords

        self.tracker_label = tracker_label
        if tracker_label == "word-overlap":
            if use_stopwords:
                self.tracker_label = f"{tracker_label}.w_stopwords"

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Word Overlap</h{header}>"
        html += "<p>This measurement calculates the word overlap between "
        html += "two items "
        if self.stopwords:
            html += "with the use of stop words.</p>"
        else:
            html += "without the consideration of stop words.</p>"

        return html

    def compare(
        self,
        a: Union[str, PresentableRecord],
        b: Union[str, PresentableRecord]
    ) -> float:
        """Compares two objects for word overlap.

        :param a: first object
        :type a: Union[str, PresentableRecord]
        :param b: second object
        :type b: Union[str, PresentableRecord]
        :return: the percentage of overlap
        :rtype: float
        """
        if isinstance(a, PresentableRecord):
            left = str(a)
        else:
            left = a

        if isinstance(b, PresentableRecord):
            right = str(b)
        else:
            right = b

        # and split
        l_words = left.split()
        r_words = right.split()

        # and remove stop words if asked
        if self.stopwords is not None and self.use_stopwords:
            f_left = [x.lower()
                      for x in l_words if
                      x.lower() not in self.stopwords]
            f_right = [x.lower()
                       for x in r_words if
                       x.lower() not in self.stopwords]
            return calc_overlap(a=f_left, b=f_right)

        return calc_overlap(a=l_words, b=r_words)


class DataKeyOverlap:
    """Measures overlap of keys. Assumes all lower case stopwords if set
    """

    description = "Measures the overlap of keys of two dicts"
    # for blueprint factory use
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "data-key-overlap",
        "arguments": {
            "tracker_label": ArgumentSetting(
                help_str="The label for a metric tracker",
                default_value="data-key-overlap",
                argument_type=ArgumentType.STRING)
        }
    }
    features = MeasurementFeatures(
        count_min=2,
        count_max=2,
        input_type=[MeasInputType.DICTIONARY,
                    MeasInputType.PRESENTABLE_RECORD],
        output_type=MeasOutputType.FLOAT,
        can_use_stopwords=False)

    def __init__(self, tracker_label: str = "data-key-overlap"):
        self.tracker_label = tracker_label

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"key Overlap<h/{header}>"
        html += "<p>This measurement calculates the key overlap between "
        html += "two items </p>"

        return html

    def compare(
        self,
        a: Union[dict, PresentableRecord],
        b: Union[dict, PresentableRecord],
    ) -> float:
        """Compares two objects keys for overlap. Two with the same
        exact key entries will return 1.

        :param a: first object
        :type a: Union[str, PresentableRecord]
        :param b: second object
        :type b: Union[str, PresentableRecord]
        :return: the percentage of overlap
        :rtype: float
        """

        # pre-process
        if isinstance(a, PresentableRecord):
            a_data = a.create_copy_of_data()
        elif isinstance(a, dict):
            a_data = a
        else:
            msg = f"Invalid type for a: {type(a)}"
            raise TypeError(msg)

        if isinstance(b, PresentableRecord):
            b_data = b.create_copy_of_data()
        elif isinstance(b, dict):
            b_data = b
        else:
            msg = f"Invalid type for a: {type(a)}"
            raise TypeError(msg)

        a_key_lower = []
        b_key_lower = []

        for key in a_data.keys():
            a_key_lower.append(key.lower())

        for key in b_data.keys():
            b_key_lower.append(key.lower())

        return calc_overlap(a=a_key_lower, b=b_key_lower)


class DataValueOverlap:
    """Measures overlap of values by converting all values into a
    single string and calc_overlap function. Assumes all lower case
    stopwords if set
    """
    description = "Compares the word overlap between two dicts values"
    # for blueprint factory use
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "data-value-word-overlap",
        "arguments": {
            "tracker_label": ArgumentSetting(
                help_str="The label for a metric tracker",
                default_value="word-overlap",
                argument_type=ArgumentType.STRING),
            "use_stopwords": ArgumentSetting(
                help_str="Use stopwords",
                default_value=False,
                argument_type=ArgumentType.BOOL)
        }
    }
    features = MeasurementFeatures(
        count_min=2,
        count_max=2,
        input_type=[MeasInputType.DICTIONARY,
                    MeasInputType.PRESENTABLE_RECORD],
        output_type=MeasOutputType.FLOAT,
        can_use_stopwords=True)

    def __init__(
        self,
        tracker_label: str = "data-value-overlap",
        use_stopwords: bool = False
    ):
        self.tracker_label = tracker_label
        if tracker_label == "data-value-overlap":
            if use_stopwords:
                self.tracker_label = f"{tracker_label}.w_stopwords"

        self.use_stopwords = use_stopwords
        self.stopwords: list[str] = []

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Data value Overlap<h/{header}>"
        html += "<p>This measurement calculates the word overlap between "
        html += "two items for only the values, not the keys "
        if self.stopwords:
            html += "with the use of stop words.</p>"
        else:
            html += "without the consideration of stop words.</p>"

        return html

    def _prepare_data(self, data: dict) -> list[str]:
        """Performs the transformation of a dict into a list of words
        that the calc_overlap function will use. If there are stopwords
        defined they will be removed here.

        :param data: the data to process
        :type data: dict
        :return: the words prepared for the calc_overlap function
        :rtype: list[str]
        """

        tmp = []
        for value in data.values():
            if isinstance(value, str):
                tmp_split = value.split()
                for tmp_val in tmp_split:
                    if self.stopwords is not None and self.use_stopwords:
                        if tmp_val.lower() not in self.stopwords:
                            tmp.append(tmp_val)
                    else:
                        tmp.append(tmp_val)

            elif isinstance(value, Number):
                tmp.append(str(value))

        return tmp

    def compare(
        self,
        a: Union[dict, PresentableRecord],
        b: Union[dict, PresentableRecord],
    ) -> float:
        """Compares two objects for word overlap in the values of the
        data. This measurement takes both string and numbers and
        converts them into a single string for an object. These two
        strings are then compared looking for word overlap.

        :param a: first object
        :type a: Union[str, PresentableRecord]
        :param b: second object
        :type b: Union[str, PresentableRecord]
        :return: the percentage of overlap
        :rtype: float
        """
        # pre-process
        if isinstance(a, PresentableRecord):
            a_data = a.create_copy_of_data()
        elif isinstance(a, dict):
            a_data = a
        else:
            msg = f"Invalid type for a: {type(a)}"
            raise TypeError(msg)

        if isinstance(b, PresentableRecord):
            b_data = b.create_copy_of_data()
        elif isinstance(b, dict):
            b_data = b
        else:
            msg = f"Invalid type for b: {type(b)}"
            raise TypeError(msg)

        a_words = self._prepare_data(a_data)
        b_words = self._prepare_data(b_data)
        return calc_overlap(a=a_words, b=b_words)


# ---------------------------------------------------------------------
# Group wrappers
# ---------------------------------------------------------------------

class GroupWordOverlap:
    """Provides a wrapper for the WordOverlap in order to parse a
    PresentationGroup with two entries."""

    description = "Compares the word overlap for a PresentableGroup"
    # for blueprint factory use
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "group-word-overlap",
        "arguments": {
            "tracker_label": ArgumentSetting(
                help_str="The label for a metric tracker",
                default_value="g-word-overlap",
                argument_type=ArgumentType.STRING),
            "use_stopwords": ArgumentSetting(
                help_str="Use stop-words",
                default_value=False,
                argument_type=ArgumentType.BOOL)
        }
    }

    features = MeasurementFeatures(
        input_type=[MeasInputType.PRESENTABLE_GROUP],
        output_type=MeasOutputType.FLOAT,
        count_min=2,
        count_max=2,
        can_use_stopwords=True)

    def __init__(
        self,
        use_stopwords: bool = False,
        tracker_label: str = "word-overlap"
    ):
        # uses the above measurement. This is a wrapper.
        self.stopwords = use_stopwords
        self._meas = WordOverlap(
            use_stopwords=use_stopwords,
            tracker_label=tracker_label)

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Group Word Overlap<h/{header}>"
        html += "<p>This measurement calculates the word overlap between "
        html += "two items "
        if self.stopwords:
            html += "with the use of stop words.</p>"
        else:
            html += "without the consideration of stop words.</p>"

        return html

    def measure(self, a: PresentableGroup) -> float:
        """Performs the measurement based on a group with two records

        :param a: The group to measure
        :type a: PresentableGroup
        :return: The measurement results
        :rtype: Any
        """
        # transform
        return self._meas.compare(
            a=a[0],
            b=a[1])


class GroupDataKeyOverlap:
    """Provides a wrapper for the DataKeyOVerlap in order to parse a
    PresentationGroup with two entries."""

    description = "compares the key overlap for a PresentableGroup"
    # for blueprint factory use
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "g-data-key-overlap",
        "arguments": {
            "tracker_label": ArgumentSetting(
                help_str="The label for a metric tracker",
                default_value="g-data-key-overlap",
                argument_type=ArgumentType.STRING)
        }
    }
    features = MeasurementFeatures(
        input_type=[MeasInputType.PRESENTABLE_GROUP],
        output_type=MeasOutputType.FLOAT,
        count_min=2,
        count_max=2,
        can_use_stopwords=False)

    def __init__(self, tracker_label: str = "g-data-key-overlap"):
        self.tracker_label = tracker_label
        self._meas = DataKeyOverlap(tracker_label=tracker_label)

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Group key Overlap<h/{header}>"
        html += "<p>This measurement calculates the key overlap between "
        html += "two items </p>"

        return html

    def measure(self, a: PresentableGroup) -> float:
        """Performs the measurement based on a group with two records

        :param a: The group to measure
        :type a: PresentableGroup
        :return: The measurement results
        :rtype: Any
        """
        # transform
        return self._meas.compare(
            a=a[0],
            b=a[1])


class GroupDataValueOverlap:
    """Provides a wrapper for the DataKeyOVerlap in order to parse a
    PresentationGroup with two entries."""

    description = "compares the value overlap for a PresentableGroup"
    # for blueprint factory use
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "g-data-value-word-overlap",
        "arguments": {
            "tracker_label": ArgumentSetting(
                help_str="The label for a metric tracker",
                default_value="g-data-key-overlap",
                argument_type=ArgumentType.STRING),
            "use_stopwords": ArgumentSetting(
                help_str="Use stop-words",
                default_value=False,
                argument_type=ArgumentType.BOOL)
        }
    }
    features = MeasurementFeatures(
        input_type=[MeasInputType.PRESENTABLE_GROUP],
        output_type=MeasOutputType.FLOAT,
        count_min=2,
        count_max=2,
        can_use_stopwords=False)

    def __init__(
            self,
            tracker_label: str = "g-data-value-overlap",
            use_stopwords: bool = False):
        self.tracker_label = tracker_label
        self.stopwords = use_stopwords
        self._meas = DataValueOverlap(
            tracker_label=tracker_label, use_stopwords=use_stopwords)

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Group Data value Overlap<h/{header}>"
        html += "<p>This measurement calculates the word overlap between "
        html += "two items for only the values, not the keys "
        if self.stopwords:
            html += "with the use of stop words.</p>"
        else:
            html += "without the consideration of stop words.</p>"

        return html

    def measure(self, a: PresentableGroup) -> float:
        """Performs the measurement based on a group with two records

        :param a: The group to measure
        :type a: PresentableGroup
        :return: The measurement results
        :rtype: Any
        """
        return self._meas.compare(
            a=a[0],
            b=a[1])
