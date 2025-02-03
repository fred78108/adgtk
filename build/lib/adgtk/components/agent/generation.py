"""Generative focused Agent. Used for applications where the action
is text and is not a small action space. This Agent does not measure
anything but instead provides a simple interface into the Policy and
drives training. If you need tracking against actions refer to the
BasicAgent.
"""

import logging
import os
import time
from typing import Union, cast
import yaml
from adgtk.common import (
    FactoryBlueprint,
    FolderManager,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.data import SimpleRecordStore
from adgtk.factory import ComponentFeatures, ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.tracking import PerformanceTracker
from adgtk.components import State, Action
from adgtk.components.policy import Policy
from adgtk.components.environment import Environment
from adgtk.utils import llm_output_to_list


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

LOG_EVERY_EPISODE = 1

# ----------------------------------------------------------------------
# Agent
# ----------------------------------------------------------------------


class GenerationAgent:
    """A Generation Agent."""

    description = "An agent that is focused on generating data."
    blueprint: FactoryBlueprint = {
        "group_label": "agent",
        "type_label": "generation",
        "arguments": {
            "name": ArgumentSetting(
                help_str="The Agent name. Useful when multiple agents are used",
                default_value="basic",
                argument_type=ArgumentType.STRING),
            "policy": ArgumentSetting(
                help_str="The policy to use",
                default_value="policy",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }
    features = ComponentFeatures(
        object_factory=True, experiment_journal=True)

    def __init__(
        self,
        name: str,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        policy: ComponentDef
    ) -> None:
        self.name = name
        self.factory = factory
        self.journal = journal
        # and create the policy from the Factory
        self.policy = self.factory.create(policy)
        self.policy = cast(Policy, self.policy)
        self.save_threshold: float = 0.4

    def engage(self, state: State) -> Action:
        """Engages the Policy for a single state. The goal is to exploit
        the policy not explore/train. This method will set the policy
        into exploit mode versus training mode.

        :param state: The state to invoke the Policy with
        :type state: State
        :return: The action based on the Policy
        :rtype: Action
        """
        self.policy.training = False
        result = self.policy.invoke(state)
        return result

    def train(
        self,
        experiment_name: str,
        train_environment: Environment,
        val_environment: Union[Environment, None] = None,
        test_environment: Union[Environment, None] = None,
        epochs: int = 1,
    ) -> None:
        """Explores an environment and trains the provided policy to
        learn how to predict match versus non-match for the entities.
        :param experiment_name: The name of the experiment.
        :type experiment_name: str
        :param train_environment: The env for training
        :type train_environment: Environment
        :param val_environment: validation env
        :type val_environment: Environment, optional
        :param test_environment: The test env
        :type test_environment: Environment, optional
        :param epochs:  outer epochs, for the agent not the policy
        :type epochs: int, optional
        """

        self.policy.training = True
        # setup performance tracking
        perf_tracker = PerformanceTracker(
            experiment_name=experiment_name,
            component=f"agent.{self.name}",
            last_only=False)

        perf_tracker.register_statistic(label="avg-created")
        perf_tracker.register_statistic(label="avg-creation-time")

        # folder setup
        folder_mgr = FolderManager(name=experiment_name)

        # internal dataset
        data_file = os.path.join(folder_mgr.agent, "simple-record-store.pkl")
        created_data = SimpleRecordStore(
            filename=data_file,
            load_from_disk_on_launch=False)

        for epoch in range(epochs):
            state, rollover = train_environment.reset()
            logging.info(f"Starting epoch {epoch}")
            step_count = 0
            avg_created_data = []
            avg_time_data = []
            while not rollover:
                start_time = time.perf_counter()
                step_count += 1
                # invoke Policy
                action = self.policy.invoke(state)
                # update Environment
                state, reward, rollover = train_environment.step(action)
                if step_count % LOG_EVERY_EPISODE == 0:
                    logging.info(f" - completed {step_count} episodes")
                if reward > self.save_threshold:
                    candidates = llm_output_to_list(action)
                    if len(candidates) > 0:
                        # add to the data store
                        created_data.bulk_insert(candidates)
                    avg_created_data.append(len(candidates))
                else:
                    # so we can track overall performance even when 0
                    avg_created_data.append(0)

                # update Policy
                self.policy.update(reward)

                # update time performance, "per step"
                cur_t = time.perf_counter()
                avg_time = (cur_t - start_time) / step_count
                avg_time_data.append(avg_time)

            # calculate the epoch stats
            if len(avg_created_data) > 0:
                avg_created = sum(avg_created_data) / len(avg_created_data)
            else:
                avg_created = 0
            if len(avg_time_data) > 0:
                avg_time = sum(avg_time_data) / len(avg_time_data)
            else:
                avg_time = 0

            # and write the epoch to disk
            perf_tracker.add_data(label="avg-created", value=avg_created)
            perf_tracker.add_data(label="avg-creation-time", value=avg_time)

            # now log
            logging.info(f"Completed epoch {epoch}")

            # update policy weights, etc
            self.policy.refresh()

            # save performance statistics to disk / logs

            logging.info(f"Epoch {epoch}: avg created = {avg_created}")
            logging.info(f"Epoch {epoch}: avg creation time = {avg_time}")

            perf_tracker.save_data()

            # now save the data to disk
            created_data.save_to_disk(data_file)
            raw_data = created_data.export_to_dict(filters={})
            raw_data_file = os.path.join(folder_mgr.agent, "raw-data.yaml")
            with open(raw_data_file, "w+", encoding="utf-8") as outfile:
                yaml.safe_dump(
                    data=raw_data,
                    stream=outfile,
                    default_flow_style=False,
                    sort_keys=False)
