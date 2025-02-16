"""Generative focused Agent. Used for applications where the action
is text and is not a small action space. This Agent does not measure
anything but instead provides a simple interface into the Policy and
drives training. If you need tracking against actions refer to the
BasicAgent.
"""

import logging
import os
import sys
import time
from typing import Union, cast
import pandas as pd
from adgtk.common import (
    FactoryBlueprint,
    FolderManager,
    ArgumentSetting,
    ArgumentType,
    ComponentDef)
from adgtk.factory import ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.tracking import PerformanceTracker
from adgtk.components import State, Action, StateType
from adgtk.components.data import PresentableRecord, PresentableGroup
from adgtk.components.policy import Policy, UsesPrompts
from adgtk.components.environment import Environment
from adgtk.utils import process_possible_yaml, create_line
from adgtk.instrumentation import MeasurementExecution
from structure import SimpleRecordStore

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

LOG_EVERY_EPISODE = 20
PROMPT_SAMPLE_FILE = "sample-prompts.txt"
GENERATED_FAIL_SAMPLE_FILE = "sample-failed.txt"
GENERATED_GOOD_SAMPLE_FILE = "sample-good.txt"


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def append_sample(sample: str, file_w_path: str, epoch: int = -1) -> None:
    """Appends a sample with epoch information to a file.

    :param sample: the sample to append
    :type sample: str
    :param file_w_path: the file with path to open
    :type file_w_path: str
    :param epoch: the epoch associated with this sample, defaults to 0
    :type epoch: int, optional
    """
    if epoch < 0:
        intro_line = "\n---------------------------------------\n"
    else:
        intro_line = f"\n------------ epoch {epoch} ------------\n"

    line = create_line(intro_line)

    with open(file=file_w_path, mode="a+", encoding="utf-8") as outfile:
        outfile.write(intro_line)
        outfile.write(sample)
        outfile.write("\n")
        outfile.write(line)
        outfile.write("\n")


def get_state_keys(state: State) -> list:
    """Gets the keys from the state based on the type.

    :param state: The state to extract keys from
    :type state: State
    :return: The keys from the state
    :rtype: list
    """
    list_data: list[dict]
    data: dict
    if state.state_type == StateType.STRING:
        list_data = process_possible_yaml(state.value)
        if isinstance(list_data[0], dict):
            return list(list_data[0].keys())
    elif state.state_type == StateType.DICT:
        if isinstance(state.value, dict):
            return list(state.value.keys())
    elif state.state_type == StateType.PRESENTABLE_RECORD:
        if isinstance(state.value, PresentableRecord):
            data = state.value.create_copy_of_data()
            return list(data.keys())
    elif state.state_type == StateType.PRESENTABLE_GROUP:
        if isinstance(state.value, PresentableGroup):
            if len(state.value) > 0:
                data = state.value[0].create_copy_of_data()
                return list(data.keys())

    # should not make it here unless there is a problem
    msg = f"Unexpected State processing for type {state.state_type.name}."
    logging.error(msg)
    return []

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
            "save_threshold": ArgumentSetting(
                help_str="The minimum reward to identify as a successful generation",
                default_value=0.8,
                argument_type=ArgumentType.FLOAT),
            "drop_unexpected_columns": ArgumentSetting(
                help_str="When saving data drop columns not in the state?",
                default_value=False,
                argument_type=ArgumentType.BOOL),
            "policy": ArgumentSetting(
                help_str="The policy to use",
                group_label="policy",
                argument_type=ArgumentType.BLUEPRINT),
            "synthetic_data_measurements": ArgumentSetting(
                help_str="The measurements to take with the data created",
                group_label="measurement-engine",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }

    def __init__(
        self,
        name: str,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        policy: ComponentDef,
        synthetic_data_measurements: ComponentDef,
        save_threshold: float = 0.4,
        drop_unexpected_columns: bool = False
    ) -> None:
        self.name = name
        self.factory = factory
        self.journal = journal
        # and create the policy from the Factory
        self.policy = self.factory.create(policy)
        self.policy = cast(Policy, self.policy)
        self.save_threshold: float = save_threshold
        self.drop_unexpected_columns = drop_unexpected_columns
        self.syn_data_meas_engine: MeasurementExecution
        self.syn_data_meas_engine = factory.create(synthetic_data_measurements)

        if self.journal is None:
            logging.error("Agent is missing the journal")
            sys.exit(1)

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
        if val_environment is None:
            logging.info("You should implement this")
        if test_environment is None:
            logging.info("You should implement this")

        # need to ensure int. observed during real-world usage.
        try:
            epochs = int(epochs)        # ensure consistent
        except ValueError:
            msg = f"Invalid epochs value of {epochs}"
            logging.error(msg)
            sys.exit(1)

        self.policy.training = True
        msg = "Agent is starting training with a save threshold of " \
            f"{self.save_threshold}"
        logging.info(msg)
        # setup performance tracking
        perf_tracker = PerformanceTracker(
            experiment_name=experiment_name,
            component=f"agent.{self.name}",
            last_only=False)

        perf_tracker.register_statistic(label="avg-created")
        perf_tracker.register_statistic(label="avg-creation-time")
        perf_tracker.register_statistic(label="avg-reward")

        # folder and setup
        folder_mgr = FolderManager(name=experiment_name)
        sample_prompt_w_path_file = os.path.join(
            folder_mgr.agent,
            PROMPT_SAMPLE_FILE)

        sample_fail_w_path_file = os.path.join(
            folder_mgr.agent,
            GENERATED_FAIL_SAMPLE_FILE)

        sample_good_w_path_file = os.path.join(
            folder_mgr.agent,
            GENERATED_GOOD_SAMPLE_FILE)

        if self.journal is not None:
            self.journal.log_data_write(
                description="Sample Prompts",
                file_w_path=sample_prompt_w_path_file,
                component=f"agent.{self.name}",
                entry_type="sample")

            self.journal.log_data_write(
                description="Low score generated data examples",
                file_w_path=sample_fail_w_path_file,
                component=f"agent.{self.name}",
                entry_type="sample")

            self.journal.log_data_write(
                description="passing score generated data examples",
                file_w_path=sample_good_w_path_file,
                component=f"agent.{self.name}",
                entry_type="sample")
        else:
            # should never happen but just in case.
            logging.warning("Missing journal for Agent")

        if os.path.exists(sample_prompt_w_path_file):
            msg = f"Removing {sample_prompt_w_path_file} file to log new only."
            logging.info(msg)
            os.remove(sample_prompt_w_path_file)

        if os.path.exists(sample_fail_w_path_file):
            msg = f"Removing {sample_fail_w_path_file} file to log new only."
            logging.info(msg)
            os.remove(sample_fail_w_path_file)

        if os.path.exists(sample_good_w_path_file):
            msg = f"Removing {sample_good_w_path_file} file to log new only."
            logging.info(msg)
            os.remove(sample_good_w_path_file)

        # internal dataset
        data_file = os.path.join(folder_mgr.agent, "simple-record-store.pkl")
        created_data = SimpleRecordStore(
            filename=data_file,
            load_from_disk_on_launch=False)

        for epoch in range(epochs):
            state, rollover = train_environment.reset()
            logging.info("Starting epoch %d", epoch)
            step_count = 0
            avg_created_data = []
            avg_time_data = []
            avg_reward_data = []
            sampled_prompt = False
            sampled_failed = False
            sampled_good = False
            # performance only check. no need to check everytime.
            if not isinstance(self.policy, UsesPrompts):
                sampled_prompt = True

            while not rollover:
                start_time = time.perf_counter()
                step_count += 1
                # invoke Policy
                action = self.policy.invoke(state)
                # sample?
                if not sampled_prompt:
                    sampled_prompt = True
                    # second safety check
                    if isinstance(self.policy, UsesPrompts):
                        append_sample(
                            sample=self.policy.last_prompt,
                            epoch=epoch,
                            file_w_path=sample_prompt_w_path_file)

                # update Environment
                state, reward, rollover = train_environment.step(action)
                avg_reward_data.append(reward)
                if step_count % LOG_EVERY_EPISODE == 0:
                    logging.info(" - completed %d episodes", step_count)
                if reward > self.save_threshold:
                    candidates = process_possible_yaml(action.value)

                    if self.drop_unexpected_columns:
                        expected_col = get_state_keys(state=state)
                        for sample in candidates:
                            keys_for_sample = list(sample.keys()).copy()
                            for key in keys_for_sample:
                                if key not in expected_col:
                                    sample.pop(key)

                    if not sampled_good:
                        sampled_good = True
                        append_sample(
                            sample=action.value,
                            file_w_path=sample_good_w_path_file,
                            epoch=epoch)
                        if len(candidates) == 0:
                            msg = "good reward but no samples? Sample for "\
                                f"epoch {epoch} is questionable"
                            logging.warning(msg)

                    if len(candidates) > 0:
                        # add to the data store
                        created_data.bulk_insert(candidates)
                    avg_created_data.append(len(candidates))
                    # and measure
                    self.syn_data_meas_engine.perform_measurements(candidates)

                else:
                    # so we can track overall performance even when 0
                    avg_created_data.append(0)
                    # and do we need to sample?
                    if not sampled_failed:
                        append_sample(
                            sample=action.value,
                            file_w_path=sample_fail_w_path_file,
                            epoch=epoch)

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

            if len(avg_reward_data) > 0:
                avg_reward = sum(avg_reward_data) / len(avg_reward_data)
            else:
                avg_reward = 0

            # and write the epoch to disk
            perf_tracker.add_data(label="avg-created", value=avg_created)
            perf_tracker.add_data(label="avg-creation-time", value=avg_time)
            perf_tracker.add_data(label="avg-reward", value=avg_reward)

            # now log
            logging.info("Completed epoch %d", epoch)

            # update policy weights, etc
            self.policy.refresh()

            # save performance statistics to disk / logs

            logging.info("Epoch %d : avg created = %.2f", epoch, avg_created)
            logging.info("Epoch %d : avg episode time = %.2f", epoch, avg_time)
            logging.info("Epoch %d : avg reward = %.2f", epoch, avg_reward)

            perf_tracker.save_data()

            # now save the data to disk
            created_data.save_to_disk(data_file)
            raw_data = created_data.export_to_dict(filters={})

            filename_w_path = os.path.join(
                folder_mgr.dataset, f"{self.name}.generated.csv")

            self.journal.log_data_write(
                description="Synthetic data generated",
                component=f"agent.{self.name}",
                entry_type="created",
                file_w_path=filename_w_path)

            df = pd.DataFrame(raw_data["data"])
            df.to_csv(filename_w_path)
            msg = f"Saved synthetic data to {filename_w_path}."
            logging.info(msg)
            str_filename_w_path = os.path.join(
                folder_mgr.dataset, f"{self.name}.str-generated.csv")

            self.journal.log_data_write(
                description="Synthetic data string representation",
                component=f"agent.{self.name}",
                entry_type="created",
                file_w_path=str_filename_w_path)

            df_str = pd.DataFrame(raw_data["string_rep"])
            df_str.to_csv(str_filename_w_path)
            msg = f"Saved synthetic string_rep to {str_filename_w_path}."
            logging.info(msg)
