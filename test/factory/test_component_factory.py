# pyright: reportIncompatibleVariableOverride=false
# pyright: reportArgumentType=false
# pyright: reportFunctionMemberAccess=false

"""test_component_factory.py Used for testing the factory
for dynamic objects.

Testing
=======
py -m pytest -s test/factory/test_component_factory.py

Note: Initial test plan created by a model, modified and updated to
meet my needs and addressed issues (created with errors, etc).
"""
import pytest   # type: ignore
from adgtk.factory import component
from adgtk.factory.structure import (
    BlueprintQuestion,
    FactoryOrder,
    SupportsFactory
)

@pytest.fixture(autouse=True)
def clear_factory_registry():
    # Clear global state between tests for isolation
    component._inventory.clear()
    component._groups.clear()

def dummy_creator(foo=None):
    return {"foo": foo}

class DummyFactoryClass(SupportsFactory):
    factory_id: str = "dummy-factory-class"
    group: str = "dummy-group"
    tags: list[str] = ["test", "class"]
    interview_blueprint: list[BlueprintQuestion] = [
        BlueprintQuestion(
            attribute="foo",
            question="Enter foo",
            entry_type="str"
        )
    ]
    summary: str = "A dummy SupportsFactory class"
    def __call__(self, foo=None):
        return {"foo": foo}


def test_factory_can_init_behavior():
    class CanInitClass(SupportsFactory):
        factory_id = "can-init"
        group = "init-group"
        tags = []
        summary = "test"
        interview_blueprint = []
        factory_can_init = True
        def __call__(self, **kwargs):
            return kwargs
        def __init__(self, foo:int) -> None:
            self.foo = foo
            super().__init__()

    fid = component.register(CanInitClass)
    entry = component._inventory[fid]
    assert entry.factory_can_init is True
    result = component.create(fid, foo=42)    
    assert result.foo == 42


def test_factory_id_int_like_string_raises():
    with pytest.raises(ValueError):
        component.register(dummy_creator, group="g", factory_id="42")


def test_get_callable_returns_creator():
    fid = component.register(dummy_creator, group="callable-test")
    creator = component.get_callable(fid)
    assert creator is dummy_creator


def test_entry_and_group_exists():
    fid = component.register(dummy_creator, group="exists-group")
    assert component.entry_exists(fid)
    assert component.group_exists("exists-group")
    component.remove(fid)
    assert not component.entry_exists(fid)


def test_get_group_names_contains_registered_group():
    group_name = "gnames"
    component.register(dummy_creator, group=group_name)
    assert group_name in component.get_group_names()

def test_register_basic_callable():
    fid = component.register(dummy_creator, group="dummies", tags=["alpha"], summary="basic test")
    assert fid in component._inventory
    entry = component._inventory[fid]
    assert entry.group == "dummies"
    assert "alpha" in entry.tags
    assert entry.summary == "basic test"

def test_register_supports_factory():
    fid = component.register(
        item=DummyFactoryClass, tags=["extra"],
        group="override-group")
    assert fid in component._inventory
    entry = component._inventory[fid]
    assert "test" in entry.tags
    assert "class" in entry.tags
    assert "extra" in entry.tags
    assert entry.summary == DummyFactoryClass.summary
    assert entry.group == "override-group"
    assert entry.interview_blueprint == DummyFactoryClass.interview_blueprint

def test_register_duplicate_id_raises():
    fid = component.register(dummy_creator, group="dups", factory_id="myid")
    with pytest.raises(IndexError):
        component.register(dummy_creator, group="dups", factory_id="myid")

def test_register_non_callable_raises():
    with pytest.raises(ValueError):
        component.register(item=1234, group="dups")

def test_register_missing_group_raises():
    with pytest.raises(ValueError):
        component.register(dummy_creator)

def test_callable_success():
    fid = component.register(dummy_creator, group="fact", summary="dummy")
    obj = component.get_callable(fid)
    assert obj is dummy_creator


def test_create_unknown_id_raises():
    with pytest.raises(KeyError):
        component.create("not-exist", foo=0)

def test_create_using_order_success():
    class OrderFactoryClass(SupportsFactory):
        factory_id = "order-factory"
        group = "order-group"
        tags = []
        summary = "order test"
        interview_blueprint = []
        factory_can_init = True
        def __init__(self, foo=None):
            self.foo = foo

    fid = component.register(OrderFactoryClass)
    order = FactoryOrder(factory_id=fid, init_args={"foo": "bar"})
    obj = component.create_using_order(order)
    assert isinstance(obj, OrderFactoryClass)
    assert obj.foo == "bar"

def test_create_using_order_invalid_raises():
    with pytest.raises(Exception):
        component.create_using_order(123)

def test_get_interview_success():
    fid = component.register(
        dummy_creator,
        group="interview",
        interview_blueprint=[BlueprintQuestion(
            attribute="foo",
            question="Your foo?",
            entry_type="str"
        )]
    )
    interview = component.get_interview(fid)
    assert isinstance(interview, list)
    assert interview[0].attribute == "foo"
    assert interview[0].question == "Your foo?"

def test_get_interview_unknown_raises():
    with pytest.raises(KeyError):
        component.get_interview("does-not-exist")

def test_remove_success():
    fid = component.register(dummy_creator, group="rm", summary="to remove")
    component.remove(fid)
    assert fid not in component._inventory

def test_remove_unknown_raises():
    with pytest.raises(KeyError):
        component.remove("unknown-id")

def test_list_entries_all():
    id1 = component.register(dummy_creator, group="x", tags=["t1"], summary="s1")
    id2 = component.register(dummy_creator, group="y", tags=["t2"], summary="s2")
    all_entries = component.list_entries()
    found_ids = [e.factory_id for e in all_entries]
    assert id1 in found_ids and id2 in found_ids

def test_list_entries_group_and_tags():
    component.register(dummy_creator, group="g", tags=["a", "b"], summary="one")
    component.register(dummy_creator, group="g", tags=["a"], summary="two")
    results = component.list_entries(tags=["a"], group="g")
    assert len(results) == 2
    results = component.list_entries(tags=["b"], group="g")
    assert len(results) == 1

def test_report_output(capsys):
    component.register(dummy_creator, group="g", tags=["x"], summary="rpt1")
    component.register(dummy_creator, group="g", tags=["y"], summary="rpt2")
    component.report(group="g")
    captured = capsys.readouterr()
    assert "Factory report" in captured.out
    assert "g".upper() in captured.out
    assert "rpt1" in captured.out
    assert "rpt2" in captured.out
