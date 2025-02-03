"""Journal foundation"""

from typing import Protocol, Union


class SupportsReportingOperations(Protocol):
    name: str

    def create_html_and_export(
        self,
        experiment_name: str,
        settings_file_override: Union[str, None] = None,
        header: int = 2,
        base_url: str = "http://127.0.0.1:8000"
    ) -> str:
        """Creates local files and returns HTML that can be used by the
            reports. In addition, exports data, builds images, etc in order
            to save and report.

            :param experiment_name: The experiment name.
            :type experiment_name: str
            :param settings_file_override: the filename of the settings file,
                defaults to None which will use the default file/path.
            :type str, optional
            :param header: The header, defaults to 1
            :type header: int, optional

            :return: HTML that can be used in a report.
            :rtype: str
            """
