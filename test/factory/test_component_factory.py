"""Testing the component factory
"""
import logging
import os
import pytest
import toml
import test.mockdata.mock as mockdata
from adgtk.common import DEFAULT_SETTINGS
from adgtk.journals import ExperimentJournal
from adgtk.factory.component import uses_factory_on_init, uses_journal_on_init
from adgtk.factory import (
    DuplicateFactoryRegistration,
    InvalidBlueprint,
    ObjectFactory)

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/factory/test_component_factory.py


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
DO_CLEANUP = True
CLEAN_BEFORE_RUN = True


# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(name="settings_file")
def temp_settings_file(request):
    with open(file="project.toml", encoding="utf-8", mode="w") as outfile:
        output = toml.dumps(DEFAULT_SETTINGS)
        outfile.write(output)

    def teardown():
        if os.path.exists("project.toml") and DO_CLEANUP:
            os.remove("project.toml")

    request.addfinalizer(teardown)


@pytest.fixture(name="loaded_factory")
def loaded_factory_fixture(settings_file):
    """Loads a factory with blueprints and components to create"""
    journal = ExperimentJournal()
    factory = ObjectFactory(journal=journal)
    factory.register(
        group_label_override="cat",
        type_label_override="tabby",
        creator=mockdata.TabbyCat)

    factory.register(
        group_label_override="pet",
        type_label_override="home",
        creator=mockdata.PetHome)

    factory.register(
        group_label_override="scenario",
        type_label_override="one",
        creator=mockdata.MockScenario)

    return factory

# ----------------------------------------------------------------------
# Samples
# ----------------------------------------------------------------------


class UsesFactory:

    def __init__(self, factory: ObjectFactory, journal: ExperimentJournal):
        pass

    def hello():
        pass


class NotUsingFactory:
    def __init__(self, name: str):
        pass

    def hello():
        pass


# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------


# ----------- helper functions -----------
def test_uses_factory_on_init_true():
    result = uses_factory_on_init(UsesFactory)
    assert result


def test_uses_factory_on_init_false():
    result = uses_factory_on_init(NotUsingFactory)
    assert not result


def test_uses_journal_on_init_true():
    result = uses_journal_on_init(UsesFactory)
    assert result


def test_uses_journal_on_init_false():
    result = uses_journal_on_init(NotUsingFactory)
    assert not result

# ----------- Factory -----------


def test_create_factory(settings_file):
    """Validates the Factory is created. Basic smoke test!"""
    journal = ExperimentJournal()
    factory = ObjectFactory(journal=journal)

    assert isinstance(factory, ObjectFactory)


def test_register(settings_file):
    """Tests the registering of a type"""
    # setup
    journal = ExperimentJournal()
    factory = ObjectFactory(journal=journal)

    # exercise
    factory.register(
        group_label_override="cat", type_label_override="tabby", creator=mockdata.TabbyCat)

    cats = factory.registry_listing("cat")
    assert len(cats) == 1


def test_unregister(settings_file):
    """Tests the unregistering of a type"""
    # setup
    journal = ExperimentJournal()
    factory = ObjectFactory(journal=journal)

    factory.register(
        group_label_override="cat", type_label_override="tabby", creator=mockdata.TabbyCat)
    factory.register(
        group_label_override="cat", type_label_override="stray", creator=mockdata.DummyClass)
    cats = factory.registry_listing("cat")
    assert len(cats) == 2
    # exercise
    factory.unregister("cat", type_label="tabby")
    cats = factory.registry_listing("cat")
    assert len(cats) == 1


def test_create_type(settings_file):
    """Tests the creation of a type"""
    # setup
    journal = ExperimentJournal()
    factory = ObjectFactory(journal=journal)

    factory.register(
        group_label_override="cat", type_label_override="tabby", creator=mockdata.TabbyCat)

    # exercise
    cat = factory.create({
        "group_label": "cat",
        "type_label": "tabby",
        'arguments': {"count": 2}
    })

    assert cat.count == 2


def test_create_type_and_group(settings_file):
    """Testing the ability to create both group and type as needed"""
    journal = ExperimentJournal()
    factory = ObjectFactory(journal=journal)

    factory.register(
        group_label_override="cat", type_label_override="tabby", creator=mockdata.TabbyCat)

    cats = factory.registry_listing("cat")
    assert len(cats) == 1


def test_type_raises(loaded_factory):
    """Tests exception handling"""
    with pytest.raises(DuplicateFactoryRegistration):
        loaded_factory.register(
            group_label_override="cat",
            type_label_override="tabby",
            creator=mockdata.DummyClass)


def test_nested_build(loaded_factory):
    """Tests that passing the factory works as expected."""
    scenario = loaded_factory.create(mockdata.MOCK_SCENARIO_DEF_ONE)
    assert scenario.pet.count == 6


def test_build_raises(loaded_factory):
    """Tests that an invalid configuration is raised."""
    with pytest.raises(InvalidBlueprint):
        loaded_factory.create(mockdata.MOCK_SCENARIO_DEF_ONE_BAD)


def test_presentation_generation(loaded_factory):
    """Tests that a factory returns the correct type"""
    loaded_factory.register(
        group_label_override="presentation",
        type_label_override="fixed",
        creator=mockdata.FixedPresentationFormat
    )
    pres = loaded_factory.create({
        "group_label": "presentation",
        "type_label": "fixed",
        "arguments": {}
    })
    result = pres.present(data={})
    assert result == mockdata.STATIC_STRING_ONE


def test_get_blueprint(loaded_factory):
    """Tests the retrival of a blueprint"""
    result = loaded_factory.get_blueprint(
        group_label="cat",
        type_label="tabby")
    assert result == mockdata.TabbyCat.blueprint
