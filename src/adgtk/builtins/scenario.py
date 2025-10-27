"""builtin.py provides built-in scenario's for testing and user usage."""

from typing import Callable, ClassVar
from adgtk.experiment.structure import ScenarioResults
from adgtk.factory import SupportsFactory, BlueprintQuestion
from adgtk.tracking.structure import ExperimentRunFolders

# ----------------------------------------------------------------------
# Interview
# ----------------------------------------------------------------------
_q1 = BlueprintQuestion(
    attribute="delay",
    question="This is the delay before saying hello",
    entry_type="float",
    default_value=1
)

_q2 = BlueprintQuestion(
    attribute="measurement",
    question="Which measurement",
    entry_type="expand",
    group="measure"
)

hello_world_interview = [
    _q1
]
nested_interview = [
    _q1,
    _q2
]

# ----------------------------------------------------------------------
# Class
# ----------------------------------------------------------------------

class HelloWorldScenario(SupportsFactory):
    """This scenario prints hello world. It is useful for testing and
    development. More importantly it is useful for validating your
    environment when you get setup as well as being used as an example.
    """
    factory_id: ClassVar = "hello.world"
    group: ClassVar = "scenario"
    tags: ClassVar = ["demo", "development"]
    summary: ClassVar = "A simple scenario to validate your environment"
    interview_blueprint: ClassVar =  hello_world_interview
    factory_can_init: ClassVar = True

    def __init__(self, delay:float) -> None:        
        super().__init__()
        self.delay = delay


    def run_scenario(
        self,
        result_folders:ExperimentRunFolders
    ) -> ScenarioResults:
        print(f"Hello World from the Scenario! - attr={self.delay}")
        return ScenarioResults(files=[])

class NestedWorld(SupportsFactory):
    """A demo Scenario that will require multiple expansions
    """
    factory_id: ClassVar = "nested.world"
    group: ClassVar = "scenario"
    tags: ClassVar = ["demo", "development"]
    summary: ClassVar = "A nested scenario to validate your environment"
    interview_blueprint: ClassVar =  nested_interview
    factory_can_init: ClassVar = True

    def __init__(self, delay:float, measurement:Callable) -> None:        
        super().__init__()
        self.delay = delay        
        self.measure = measurement

    def run_scenario(
        self,
        result_folders:ExperimentRunFolders
    ) -> ScenarioResults:        
        print(f"Hello NestedWorld from the Scenario! - attr={self.delay}")
        print(f"MEAS: {self.measure}")
        return ScenarioResults(files=[])


