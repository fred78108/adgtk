"""Included Measurement scenarios. These scenarios are focused on either
measuring a dataset or a model. They provide common scenarios for any
experiment thus eliminating the need to define one. The user can and
should modify their objects as needed and register them into the factory
and use their experiment blueprint to invoke theirs instead of the base
ones used here.

Note: Uses the base objects from the factories. 
"""


import logging
from typing import cast
from adgtk.common import (
    FactoryBlueprint,
    ArgumentType,
    ArgumentSetting,
    ComponentDef)
from adgtk.factory.component import ObjectFactory, FactoryImplementable
from adgtk.instrumentation import MeasurementEngine
from adgtk.tracking import MetricTracker
from adgtk.journals import (
    ExperimentJournal,
    MetricTrackingReporter)
from adgtk.components import Processor
from adgtk.data import RecordStore
from .base import ScenarioFeatures
from .base import SCENARIO_GROUP_LABEL


class MeasureModelPerformanceScenario:

    description = "Scenario is focused on measuring model performance"
    blueprint: FactoryBlueprint = {
        "group_label": SCENARIO_GROUP_LABEL,
        "type_label": "measure_model_performance",
        "arguments": {
            "model_ckpt": ArgumentSetting(
                help_str="The model checkpoint.",
                default_value="NOT-SET",
                argument_type=ArgumentType.STRING),
            "agent": ArgumentSetting(
                help_str="The agent type",
                default_value="agent",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }

    features = ScenarioFeatures(
        object_factory=True,
        experiment_journal=True,
        performs_measurements=True,
        creates_data=False)

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        model_ckpt: FactoryBlueprint,
        agent: FactoryBlueprint
    ) -> None:
        print("SCORE!!! you have loaded a MeasModelPerf")
        pass

    def execute(self, name: str) -> None:
        """Loads a model and performs a series of measurements on it.

        :param name: The name of the experiment (for reporting, etc)
        :type name: str
        """
        print("execute - measure model")


class MeasureDatasetScenario:
    """This scenario takes a dataset and measures it against measurement
    set. Modification of the Experiment is encouraged """

    # going a bit more hard coded for now. will return to improve if
    # a better approach is found at the scenario level. For now the
    # assumption is that the scenario needs to be a bit more expclicit
    # on the object types as the use is for the most part known and
    # intended whereas going more generic in the building blocks
    # provides more flexibility.
    description = "Scenario is focused on measuring a dataset"
    blueprint: FactoryBlueprint = {
        "group_label": SCENARIO_GROUP_LABEL,
        "type_label": "measure_dataset",
        "arguments": {
            "measurement_engine": ArgumentSetting(
                help_str="The measurement engine configuration",
                default_value="measurement-engine",
                argument_type=ArgumentType.BLUEPRINT
            ),
            "datastore": ArgumentSetting(
                help_str="The datastore configuration",
                argument_type=ArgumentType.BLUEPRINT,
                default_value="datastore"),

            "dataloader": ArgumentSetting(
                help_str="The data loader",
                default_value="processing",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }

    features = ScenarioFeatures(
        object_factory=True,
        experiment_journal=True,
        performs_measurements=True,
        creates_data=False)

    def __init__(
            self,
            factory: ObjectFactory,
            journal: ExperimentJournal,
            measurement_engine: ComponentDef,
            datastore: ComponentDef,
            dataloader: ComponentDef) -> None:
        self.datastore: RecordStore = factory.create(datastore)
        self.dataloader: Processor = factory.create(dataloader)
        self.journal = journal
        # Load and cast
        self.measurement_engine = factory.create(measurement_engine)
        self.measurement_engine = cast(
            MeasurementEngine, self.measurement_engine)

        self.metric_tracker = MetricTracker()
        self.measurement_engine.update_metric_tracker(self.metric_tracker)

        # and set the datastore for the dataloader. A processor by
        # design does not have mapped a datastore. This needs to be
        # done afterwards but prior to calling process() so that the
        # factory and scenario execution remain as flexible as possible.
        self.dataloader.datastore = self.datastore

    def execute(self, name: str) -> None:
        """Loads a dataset and performs a series of measurements.

        :param name: The name of the experiment (for reporting, etc)
        :type name: str
        """
        logging.info("Starting dataloader process")
        self.dataloader.process()
        logging.info("Data has been loaded. Measuring now")
        self.measurement_engine.perform_measurements(
            data=self.dataloader.datastore)
        logging.info("Measuring complete")
        # self.journal.create_report()
        # Save data to disk
        metric_reporter = MetricTrackingReporter(name=name)

        set_names = self.measurement_engine.get_measurement_set_names()
        for name in set_names:
            logging.info("Exporting data for engine "
                         f"{self.measurement_engine.name} | set {name}")
            metric_reporter.generate_csv_exports(
                metric_tracker=self.metric_tracker,
                engine_name=self.measurement_engine.name,
                meas_set_name=name)
