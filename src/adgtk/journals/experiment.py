"""The Journal collects data about an experiment and creates a markdown
document in the results folder with key information and other details to
return to experiment results in the future.
"""


# py -m pytest test/journals/test_journal.py
import logging
import os
from urllib.parse import urljoin
from typing import Literal, Union
import jinja2
from jinja2 import Environment, FileSystemLoader
from adgtk.utils import get_timestamp_now
from .base import SupportsReportingOperations
from adgtk.common import DEFAULT_JOURNAL_REPORTS_DIR, FolderManager
from adgtk.utils import load_settings


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
PREVIEW_REPORT_FILENAME = "preview.html"
REPORT_FILENAME = "report.html"

# ----------------------------------------------------------------------
# Journal
# ----------------------------------------------------------------------


class ExperimentJournal:
    """Central place for different components to register comments, etc.
    Will also be responsible for creating reports using Jinja2 templates
    that are in the users template directory. This way the user is free
    to update CSS or similar from the template."""

    def __init__(
        self,
        use_formatting: bool = True,
        settings_file_override: Union[str, None] = None
    ) -> None:
        self.settings_file_override = settings_file_override
        self.use_formatting = use_formatting
        self._scenario_def: str = "NOT-SET"
        self._comments: list[str] = []
        self._measurements: list[str] = []
        self._data_created: dict[str, list] = {}
        self._data_sample: dict[str, list] = {}
        self._data_other: dict[str, list] = {}
        self._data_global: list[str] = []

       # now load the settings and set the items to manage
        try:
            settings = load_settings(file_override=settings_file_override)
        except FileNotFoundError as e:
            if settings_file_override is not None:
                msg = f"Unable to locate settings file {settings_file_override}"
            else:
                msg = "Unable to locate settings file from default location"
            logging.error(msg)
            raise FileNotFoundError(msg) from e

        # public and can be read/written but not worth cluttering params
        # these should not change often and likely only in special
        # cases such as dynamic sub-experiments, etc.
        self.report_folder = DEFAULT_JOURNAL_REPORTS_DIR
        self.preview_report_filename = PREVIEW_REPORT_FILENAME
        self.report_filename = REPORT_FILENAME
        self.engines: list[SupportsReportingOperations] = []
        server_proto = settings.server["proto"]
        server_host = settings.server["host"]
        server_port = settings.server["port"]
        self.base_url = f"{server_proto}://{server_host}:{server_port}"

    def register_meas_engine(self, engine: SupportsReportingOperations) -> None:
        """Registers a measurement engine for reporting purposes

        :param engine: The engine
        :type engine: SupportsReportingOperations
        """
        logging.info(f"Journal registered {engine.name}")
        self.engines.append(engine)

    def reset(self) -> None:
        """clears all data from the internal structure.
        """
        self._scenario_def = "NOT-SET"
        self._comments = []
        self._measurements = []
        self._data_created = {}
        self._data_other = {}
        self._data_sample = {}
        self._data_global = []

    def generate_preview(
        self,
        experiment_name: str,
        experiment_folder: str
    ) -> None:
        """Generates a preview of an experiment and writes that
        preview to disk.

        :param experiment_name: The name of the experiments
        :type experiment_name: str
        :param experiment_folder: root folder for the experiment results
        :type experiment_folder: str
        """
        report_folder = os.path.join(experiment_folder, self.report_folder)

        if not os.path.exists(report_folder):
            os.makedirs(report_folder, exist_ok=True)

        report_filename = os.path.join(
            report_folder, self.preview_report_filename)

        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template("preview.jinja")

        try:
            output = template.render(
                experiment_name=experiment_name,
                comments=self._comments,
                measurements=self._measurements,
                scenario_def=self._scenario_def,
                data_created=self._data_created)
            with open(
                    file=report_filename,
                    encoding="utf-8",
                    mode="w") as outfile:
                outfile.write(output)
        except jinja2.exceptions.TemplateSyntaxError as e:
            logging.error("Syntax error with preview.jinja")
            # for debugging/troubleshooting uncomment
            # raise e

    def generate_report(self, experiment_name: str) -> None:
        """Generates a preview of an experiment and writes that
        preview to disk.

        :param experiment_name: The name of the experiments
        :type experiment_name: str
        """
        folders = FolderManager(
            name=experiment_name,
            settings_file_override=self.settings_file_override)

        measurement_html = "<div><h1>Measurements</h1>"
        for engine in self.engines:
            # TODO: refactor this method to use the new settings file design
            # or pass in a folder manager from this object. For now not
            # supporting the settings file override
            measurement_html += engine.create_html_and_export(
                experiment_name=experiment_name, base_url=self.base_url,
                header=2)

        data_html = self._create_data_section(preview=False)

        report_folder = os.path.join(folders.base_folder, self.report_folder)

        if not os.path.exists(report_folder):
            os.makedirs(report_folder, exist_ok=True)

        report_filename = os.path.join(report_folder, self.report_filename)

        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template("report.jinja")
        date_ran = get_timestamp_now(include_time=True)
        try:
            output = template.render(
                date_ran=date_ran,
                experiment_name=experiment_name,
                comments=self._comments,
                measurement_section=measurement_html,
                scenario_def=self._scenario_def,
                data_section=data_html)
            with open(
                    file=report_filename,
                    encoding="utf-8",
                    mode="w") as outfile:
                outfile.write(output)
        except jinja2.exceptions.TemplateSyntaxError as e:
            logging.error("Syntax error with report.jinja")
            # for debugging/troubleshooting uncomment
            # raise e

    def _create_html_link(
        self,
        description: str,
        file_w_path: str
    ) -> str:

        url_str = urljoin(base=self.base_url, url=file_w_path)
        return f"<a href={url_str}>{description}</a>"

    def _create_data_section(self, preview: bool = False) -> str:
        html = """<div>
        <h2>Data</h2>
        """
        if len(self._data_global) > 0:
            html += r"<h3>global</h3>"
            for entry in self._data_global:
                html += r"<li>"
                html += entry
                html += r"</li>"

        for component in self._data_sample:
            html += f"<h3>{component}<h3>\n<h4>Created</h4><ul>\n"
            # Created
            for entry in self._data_created[component]:
                html += r"<li>"
                html += entry
                html += r"</li>"
            # Samples
            if len(self._data_sample[component]) > 0:
                html += r"</ul><h4>Samples</h4><ul>"
                for entry in self._data_sample[component]:
                    html += r"<li>"
                    html += entry
                    html += r"</li>"
            # Other
            if len(self._data_other[component]) > 0:
                html += r"</ul><h4>Other</h4><ul>"
                for entry in self._data_other[component]:
                    html += r"<li>"
                    html += entry
                    html += r"</li>"
            html += r"</ul></div>"

        return html

    def log_data_write(
        self,
        description: str,
        file_w_path: str,
        experiment_name: str,
        entry_type: Literal["sample", "created", "other"],
        component: Union[str, None] = None
    ) -> None:
        logging.info(f"data write: {description} {file_w_path}")
        if component is not None:
            # ensure consistency across data logs
            if component not in self._data_sample:
                self._data_sample[component] = []
            if component not in self._data_created:
                self._data_created[component] = []
            if component not in self._data_other:
                self._data_other[component] = []

        # now log
        html = f"{description} "
        html += self._create_html_link(
            description=file_w_path, file_w_path=file_w_path)

        if component is None:
            if html not in self._data_global:
                self._data_global.append(html)
        elif entry_type == "sample":
            if html not in self._data_sample[component]:
                self._data_sample[component].append(html)
        elif entry_type == "created":
            if html not in self._data_created[component]:
                self._data_created[component].append(html)
        elif entry_type == "other":
            if html not in self._data_other[component]:
                self._data_other[component].append(html)

    def add_entry(
        self,
        entry_type: Literal["comment", "scenario_def", "measurement"],
        entry_text: str,
        component: Union[str, None] = None,
        include_timestamp: bool = False
    ) -> None:

        # if a scenario definition then no formatting or appending
        if entry_type == "scenario_def":
            self._scenario_def = entry_text
            return None

        # if its not a scenario definition then add the data
        entry = ""
        if include_timestamp:
            entry += get_timestamp_now()

        if component is not None:
            if self.use_formatting:
                entry = f"  <b>{component} : </b>"
            else:
                entry = f"  {component} : "

        entry += entry_text

        # avoid duplicate entries for reporting benefits. check here
        # just in case duplicate messages are sent from the objects such
        # as an Agent logging each loop the same "Save to file"  etc.
        if entry_type == "comment":
            if entry not in self._comments:
                self._comments.append(entry)
        elif entry_type == "measurement":
            if entry not in self._measurements:
                self._measurements.append(entry)
