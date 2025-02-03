"""Measurement scenario for a dataset
"""

import logging
from typing import cast
from adgtk.common import (
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.components.data import RecordStore
from adgtk.factory.component import ObjectFactory
from adgtk.instrumentation import MeasurementEngine
from adgtk.journals import ExperimentJournal
from adgtk.scenario import SCENARIO_GROUP_LABEL
from adgtk.tracking import MetricTracker
from processing import Processor


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
        "introduction" : """The Measure Dataset Scenario will load a file from disk and perform a series of measurements on it. The scenario will load the data, perform the measurements, and save the results.

    You will configure 3 key components:
    - a meaurement engine where you will define your measurements
    - a datastore where the data will be loaded into for processing
    - a processor which will take your source data and load it into the datastore.
""",
        "arguments": {
            "measurement_engine": ArgumentSetting(
                help_str="The measurement engine configuration",
                group_label="measurement-engine",
                argument_type=ArgumentType.BLUEPRINT
            ),
            "datastore": ArgumentSetting(
                help_str="The datastore configuration",
                argument_type=ArgumentType.BLUEPRINT,
                group_label="datastore"),

            "dataloader": ArgumentSetting(
                help_str="The data loader",
                group_label="processing",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        measurement_engine: ComponentDef,
        datastore: ComponentDef,
        dataloader: ComponentDef
    ) -> None:
        self.datastore: RecordStore = factory.create(datastore)
        self.dataloader: Processor = factory.create(dataloader)
        self.journal = journal
        # Load and cast
        self.measurement_engine = factory.create(measurement_engine)
        self.measurement_engine = cast(
            MeasurementEngine, self.measurement_engine
        )

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
            data=self.dataloader.datastore
        )
        logging.info("Measuring complete")
