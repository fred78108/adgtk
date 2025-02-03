"""The Journal collects data about an experiment and creates a markdown
document in the results folder with key information and other details to
return to experiment results in the future.
"""


# py -m pytest test/journals/test_journal.py
import os
import logging
from typing import List, Union
from jinja2 import Environment, FileSystemLoader
from adgtk.utils import get_timestamp_now, create_line
from adgtk.common import (
    FactoryBlueprint,
    ComponentDef,
    convert_exp_def_to_string)


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Journal
# ----------------------------------------------------------------------


class ExperimentJournal:
    """Focused on tracking and reporting of experiment highlights. The
    goal is to create an easy to read markdown report in the results."""

    def __init__(
        self,
        experiment_name: str = "default",
        results_folder: str = "results",
        run_notes: Union[str, None] = None,
        blueprint: Union[FactoryBlueprint, None] = None
    ) -> None:

        # ------------------
        # Experiment details
        # ------------------
        self.results_folder = results_folder
        self.experiment_name = experiment_name
        self.experiment_comments = ""
        self.run_notes = run_notes
        self.blueprint = blueprint
        self.experiment_def: Union[FactoryBlueprint, ComponentDef]

        # -----------
        # Stored data
        # -----------
        # factory->group->type
        self.factory_registry: dict[str, dict[str, List[str]]] = {}

        # cleanup/merge back in ?
        self.comments: List[str] = []
        self.agent_config_higlights: List[str] = []
        self.env_config_highlights: dict[str, List[str]] = {}
        self.meas_eng_config_highlights: dict[str, List[str]] = {}
        self.measurement_highlights: dict[str, List[str]] = {}
        self.last_measurement_report_data: dict[str, dict] = {}

        # public and can be read/written but not worth cluttering params
        # these should not change often and likely only in specicial
        # cases such as dynamic sub-experiments, etc.
        self.report_folder = "reports"
        self.preview_report_filename = "preview.html"
        self.report_filename = "report.html"

        logging.info("ExperimentJournal initialized for %s", experiment_name)

    def generate_preview(self, to_console: bool = False) -> None:
        """Generates a preview of an experiment and writes that
        preview to disk.

        :param to_console: print to console, defaults to False
        :type to_console: bool, optional
        """
        report_folder = os.path.join(
            self.results_folder, self.experiment_name, self.report_folder)

        if not os.path.exists(report_folder):
            os.makedirs(report_folder, exist_ok=True)

        report_filename = os.path.join(
            report_folder, self.preview_report_filename)

        env = Environment(loader=FileSystemLoader('templates'))

        template = env.get_template("preview.jinja")
        blueprint = convert_exp_def_to_string(self.experiment_def)
        output = template.render(
            experiment_name=self.experiment_name,
            experiment_comments=self.experiment_comments,
            blueprint=blueprint)

        if to_console:
            line = create_line(modified=80)
            print(line)
            print("Preview report:")
            print(blueprint)

        with open(file=report_filename, encoding="utf-8", mode="w") as outfile:
            outfile.write(output)

    def add_factory_registration(
        self,
        factory: str,
        group_label: str,
        type_label: str
    ) -> None:
        if not factory in self.factory_registry:
            self.factory_registry[factory] = {}

        if group_label not in self.factory_registry[factory]:
            self.factory_registry[factory][group_label] = [type_label]
        else:
            self.factory_registry[factory][group_label].append(type_label)


# ----------------------------------------------------------------------
# Merge below, cleanup and test
# ----------------------------------------------------------------------

    def add_latest_report_data(self, component: str, data: dict):
        """Add data to the report.

        Args:
            component (str): The component adding the data
            data (dict): the data to add
        """
        # creates or overwrites. again, all we care about is the last.
        self.last_measurement_report_data[component] = data

    def add_comments(self, text: str, include_time: bool = False) -> None:
        """Add a comment.

        Args:
            text (str): the comment
            include_time (bool, optional): use timestamp?
                Defaults to False.
        """
        if include_time:
            self.comments.append(f"- {get_timestamp_now()} : {text}\n")
        else:
            self.comments.append(f"- {text}\n")

    def add_meas_eng_config_highlights(
        self,
        component: str,
        text: str
    ) -> None:
        """Add a highlight of a measurement engine config

        Args:
            component (str): The component reporting
            text (str): the highlight
        """
        if component not in self.meas_eng_config_highlights.keys():
            self.meas_eng_config_highlights[component] = []

        self.meas_eng_config_highlights[component].append(f"- {text}\n")

    def add_measurement_highlight(self, component: str, text: str) -> None:
        """Add a highlight of a measurement

        Args:
            component (str): The component reporting
            text (str): the result
        """

        # add if not already there
        if component not in self.measurement_highlights.keys():
            self.measurement_highlights[component] = []

        self.measurement_highlights[component].append(
            f"- {component} || ``{text}``\n")

    def add_agent_config_highlight(self, component: str, text: str) -> None:
        """Add a highlight of a agent config

        Args:
            component (str): The agent reporting
            text (str): the comment
        """

        self.agent_config_higlights.append(f"- {component} || {text}\n")

    def add_env_config_highlight(
        self,
        env_type: str,
        component: str,
        text: str
    ) -> None:
        """Add a highlight of a env config

        Args:
            env_type (str): The env reporting
            text (str): the highlight
        """

        # safety check. add if it doesn't exist:
        if env_type not in self.env_config_highlights.keys():
            self.env_config_highlights[env_type] = []

        self.env_config_highlights[env_type].append(
            f"- {component} || {text}\n")

    def create_report(self, preview: bool = False) -> None:
        """Creates a report in the results folder. It can and will be
        overwritten multiple times (as needed) through the course of the
        experiment.

        TODO: move to a Jinja template?

        Args:
            preview (bool): Generate a preview report

        """
        if preview:
            file_w_path = os.path.join(
                self.results_folder,
                self.experiment_name,
                self.preview_report_filename)
        else:
            file_w_path = os.path.join(
                self.results_folder,
                self.experiment_name,
                self.report_filename)

        logging.info("Writing report to %s", file_w_path)

        with open(file_w_path, "w", encoding="utf-8") as outfile:
            # create header
            outfile.write(f"# {self.experiment_name} Journal Report\n")
            if preview:
                outfile.write("Preview created at: ")
                timestamp = get_timestamp_now(include_time=True)
                outfile.write(f"**{timestamp}**\n\n")
            else:
                outfile.write("Date: ")
                timestamp = get_timestamp_now(include_time=False)
                outfile.write(f"**{timestamp}**\n\n")
            outfile.write(f"{self.run_notes}\n")
            outfile.write("## Reviewing output\n")
            outfile.write("Review the outcome of your experiment at:\n")
            outfile.write("- **Tensorboard data:**\n")
            # Care must be taken here as markdown needs specific spacing
            # in order to properly format the command:
            outfile.write("\n")
            msg = "        tensorboard --logdir "\
                f"runs/{self.experiment_name} --bind_all --port=6006\n"
            outfile.write(msg)
            outfile.write("\n")

            outfile.write(f"- **logs:** logs/{self.experiment_name}.log\n")
            folder_w_path = os.path.join(
                self.results_folder, self.experiment_name)
            outfile.write(f"- **saved measurements**: {folder_w_path}\n")

            # Agent
            outfile.write("\n## Configuration Highlights\n")
            only_header = True
            if len(self.agent_config_higlights) > 0:
                only_header = False
                outfile.write("### Agent\n")
                outfile.writelines(self.agent_config_higlights)

            # Environment(s)
            # note, not all experiments have an Environment
            env_count = len(list(self.env_config_highlights.keys()))
            only_header = False
            if env_count > 0:
                outfile.write("\n### Environment(s)\n")
                for env, entries in self.env_config_highlights.items():
                    outfile.write(f"#### {env}\n")
                    outfile.writelines(entries)

            m_count = len(list(self.meas_eng_config_highlights.keys()))
            if m_count > 0:
                only_header = False
                outfile.write("\n### Measurement Engine(s)\n")
                for eng, val in self.meas_eng_config_highlights.items():
                    outfile.write(f"\n#### {eng}\n")
                    outfile.writelines(val)

            if only_header:
                outfile.write(
                    "\nNo highlights recorded for this experiment.\n")

            # now the notes
            outfile.write("\n## Experiment comments\n")
            outfile.writelines(self.comments)

            # And the measurements
            report_count = len(list(self.last_measurement_report_data.keys()))
            if report_count > 0:
                outfile.write("\n## Last measurements\n")
                for comp, data in self.last_measurement_report_data.items():
                    outfile.write(f"\n### {comp}\n")
                    outfile.write("| measurement | value |\n")
                    outfile.write("| ----------- | ----- |\n")
                    for key, value in data.items():
                        if isinstance(value, int):
                            outfile.write(f"| {key} | {value} |\n")
                        else:
                            outfile.write(f"| {key} | {value:.3f} |\n")

            meas_count = len(list(self.measurement_highlights.keys()))
            if meas_count > 0:
                outfile.write("## Measurement Highlights\n")
                for component, entries in self.measurement_highlights.items():
                    outfile.write(f"### {component}\n")
                    outfile.writelines(entries)

            # and close
            outfile.close()

        if preview:
            print(f"++Preview report saved to {file_w_path}")
