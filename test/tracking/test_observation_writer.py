"""test_observation_writer.py

Unit tests for ObservationWriter and its track_step decorator.

Each test uses the ``reset_obs`` fixture (autouse) to wipe the module-level
observation store so tests are fully isolated.

Run with: pytest test/tracking/test_observation_writer.py
"""

import pytest

import adgtk.tracking.observations as obs_mod
from adgtk.tracking.observation_writer import ObservationWriter, track_step
from adgtk.tracking.observations import (
    AgentTurnObs,
    ConfigNoteObs,
    MetricEventObs,
    NoteObs,
    WarnObs,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_obs():
    """Reset module-level observation store before every test."""
    obs_mod.reset()
    yield
    obs_mod.reset()


def _all():
    """Shorthand: return all observations recorded so far."""
    return obs_mod.get_all()


# ---------------------------------------------------------------------------
# ObservationWriter.__init__
# ---------------------------------------------------------------------------

def test_init_stores_component():
    w = ObservationWriter("retriever")
    assert w.component == "retriever"


def test_init_stores_default_tags():
    w = ObservationWriter("retriever", tags=["a", "b"])
    assert w._default_tags == ["a", "b"]


def test_init_default_tags_is_defensive_copy():
    source = ["x"]
    w = ObservationWriter("retriever", tags=source)
    source.append("y")
    assert w._default_tags == ["x"]


def test_init_no_tags_gives_empty_defaults():
    w = ObservationWriter("retriever")
    assert w._default_tags == []


# ---------------------------------------------------------------------------
# _tags helper
# ---------------------------------------------------------------------------

def test_tags_includes_component_prefix():
    w = ObservationWriter("pipeline")
    result = w._tags()
    assert "component:pipeline" in result


def test_tags_component_is_first():
    w = ObservationWriter("pipeline", tags=["default"])
    result = w._tags()
    assert result[0] == "component:pipeline"


def test_tags_default_tags_follow_component():
    w = ObservationWriter("pipeline", tags=["d1", "d2"])
    result = w._tags()
    assert result == ["component:pipeline", "d1", "d2"]


def test_tags_extra_appended_after_defaults():
    w = ObservationWriter("pipeline", tags=["d1"])
    result = w._tags(["e1", "e2"])
    assert result == ["component:pipeline", "d1", "e1", "e2"]


def test_tags_does_not_mutate_instance():
    w = ObservationWriter("pipeline", tags=["d"])
    w._tags(["extra"])
    assert w._default_tags == ["d"]


# ---------------------------------------------------------------------------
# note
# ---------------------------------------------------------------------------

def test_note_emits_note_obs():
    w = ObservationWriter("comp")
    w.note("hello")
    assert len(_all()) == 1
    assert isinstance(_all()[0], NoteObs)


def test_note_message_preserved():
    w = ObservationWriter("comp")
    w.note("test message")
    assert _all()[0].message == "test message"


def test_note_component_tag_present():
    w = ObservationWriter("mycomp")
    w.note("x")
    assert "component:mycomp" in _all()[0].tags


def test_note_default_tags_merged():
    w = ObservationWriter("comp", tags=["t1"])
    w.note("x")
    assert "t1" in _all()[0].tags


def test_note_extra_tags_merged():
    w = ObservationWriter("comp")
    w.note("x", tags=["extra"])
    assert "extra" in _all()[0].tags


def test_note_tag_order():
    w = ObservationWriter("comp", tags=["d"])
    w.note("x", tags=["e"])
    assert _all()[0].tags == ["component:comp", "d", "e"]


# ---------------------------------------------------------------------------
# warn
# ---------------------------------------------------------------------------

def test_warn_emits_warn_obs():
    w = ObservationWriter("comp")
    w.warn("problem")
    assert isinstance(_all()[0], WarnObs)


def test_warn_message_preserved():
    w = ObservationWriter("comp")
    w.warn("something bad")
    assert _all()[0].message == "something bad"


def test_warn_tags_merged():
    w = ObservationWriter("comp", tags=["base"])
    w.warn("x", tags=["urgent"])
    tags = _all()[0].tags
    assert "component:comp" in tags
    assert "base" in tags
    assert "urgent" in tags


# ---------------------------------------------------------------------------
# agent_turn
# ---------------------------------------------------------------------------

def test_agent_turn_emits_correct_type():
    w = ObservationWriter("comp")
    w.agent_turn("prompt", "response")
    assert isinstance(_all()[0], AgentTurnObs)


def test_agent_turn_fields_preserved():
    w = ObservationWriter("comp")
    w.agent_turn(
        "p", "r", model="gpt-4", tokens_in=10, tokens_out=20, latency_ms=50.0
    )
    obs = _all()[0]
    assert obs.prompt == "p"
    assert obs.response == "r"
    assert obs.model == "gpt-4"
    assert obs.tokens_in == 10
    assert obs.tokens_out == 20
    assert obs.latency_ms == 50.0


def test_agent_turn_tags_merged():
    w = ObservationWriter("comp", tags=["d"])
    w.agent_turn("p", "r", tags=["e"])
    assert _all()[0].tags == ["component:comp", "d", "e"]


def test_agent_turn_optional_fields_default_none():
    w = ObservationWriter("comp")
    w.agent_turn("p", "r")
    obs = _all()[0]
    assert obs.model is None
    assert obs.tokens_in is None
    assert obs.tokens_out is None
    assert obs.latency_ms is None


# ---------------------------------------------------------------------------
# config_note
# ---------------------------------------------------------------------------

def test_config_note_emits_correct_type():
    w = ObservationWriter("comp")
    w.config_note("k", 1, "rationale")
    assert isinstance(_all()[0], ConfigNoteObs)


def test_config_note_fields_preserved():
    w = ObservationWriter("comp")
    w.config_note("top_k", 5, "default tuning")
    obs = _all()[0]
    assert obs.parameter == "top_k"
    assert obs.value == 5
    assert obs.rationale == "default tuning"


def test_config_note_tags_merged():
    w = ObservationWriter("comp", tags=["d"])
    w.config_note("k", 1, "r", tags=["e"])
    assert _all()[0].tags == ["component:comp", "d", "e"]


def test_config_note_module_level_backward_compat():
    """config_note still works without tags (backward compat)."""
    obs_mod.config_note("param", 42, "because")
    obs = _all()[0]
    assert isinstance(obs, ConfigNoteObs)
    assert obs.tags == []


def test_config_note_module_level_with_tags():
    obs_mod.config_note("param", 42, "because", tags=["t1"])
    assert "t1" in _all()[0].tags


# ---------------------------------------------------------------------------
# metric_event
# ---------------------------------------------------------------------------

def test_metric_event_emits_correct_type():
    w = ObservationWriter("comp")
    w.metric_event("accuracy", 0.9)
    assert isinstance(_all()[0], MetricEventObs)


def test_metric_event_fields_preserved():
    w = ObservationWriter("comp")
    w.metric_event("hit_rate", 0.88, step=3, note="after warmup")
    obs = _all()[0]
    assert obs.metric == "hit_rate"
    assert obs.value == 0.88
    assert obs.step == 3
    assert obs.note == "after warmup"


def test_metric_event_optional_fields_default_none():
    w = ObservationWriter("comp")
    w.metric_event("score", 1.0)
    obs = _all()[0]
    assert obs.step is None
    assert obs.note is None


def test_metric_event_tags_merged():
    w = ObservationWriter("comp", tags=["d"])
    w.metric_event("m", 1.0, tags=["e"])
    assert _all()[0].tags == ["component:comp", "d", "e"]


def test_metric_event_module_level_backward_compat():
    """metric_event still works without tags (backward compat)."""
    obs_mod.metric_event("score", 0.5)
    obs = _all()[0]
    assert isinstance(obs, MetricEventObs)
    assert obs.tags == []


def test_metric_event_module_level_with_tags():
    obs_mod.metric_event("score", 0.5, tags=["eval"])
    assert "eval" in _all()[0].tags


# ---------------------------------------------------------------------------
# track_step — success path
# ---------------------------------------------------------------------------

def test_track_step_success_emits_two_notes():
    w = ObservationWriter("comp")

    @track_step(w)
    def my_func():
        return 42

    my_func()
    recorded = _all()
    assert len(recorded) == 2
    assert all(isinstance(o, NoteObs) for o in recorded)


def test_track_step_success_entry_first():
    w = ObservationWriter("comp")

    @track_step(w)
    def my_func():
        pass

    my_func()
    assert "→ my_func" in _all()[0].message


def test_track_step_success_exit_second():
    w = ObservationWriter("comp")

    @track_step(w)
    def my_func():
        pass

    my_func()
    assert "← my_func" in _all()[1].message


def test_track_step_exit_includes_timing():
    w = ObservationWriter("comp")

    @track_step(w)
    def my_func():
        pass

    my_func()
    assert "ms" in _all()[1].message


def test_track_step_success_step_tag_on_both():
    w = ObservationWriter("comp")

    @track_step(w)
    def my_func():
        pass

    my_func()
    for obs in _all():
        assert "step" in obs.tags


def test_track_step_success_component_tag_on_both():
    w = ObservationWriter("mycomp")

    @track_step(w)
    def my_func():
        pass

    my_func()
    for obs in _all():
        assert "component:mycomp" in obs.tags


def test_track_step_preserves_return_value():
    w = ObservationWriter("comp")

    @track_step(w)
    def my_func():
        return 99

    assert my_func() == 99


def test_track_step_preserves_function_name():
    w = ObservationWriter("comp")

    @track_step(w)
    def target_function():
        pass

    assert target_function.__name__ == "target_function"


# ---------------------------------------------------------------------------
# track_step — error path
# ---------------------------------------------------------------------------

def test_track_step_error_reraises():
    w = ObservationWriter("comp")

    @track_step(w)
    def broken():
        raise ValueError("oops")

    with pytest.raises(ValueError, match="oops"):
        broken()


def test_track_step_error_emits_entry_and_warn():
    w = ObservationWriter("comp")

    @track_step(w)
    def broken():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        broken()

    recorded = _all()
    assert len(recorded) == 2
    assert isinstance(recorded[0], NoteObs)
    assert isinstance(recorded[1], WarnObs)


def test_track_step_error_warn_includes_exception_type():
    w = ObservationWriter("comp")

    @track_step(w)
    def broken():
        raise TypeError("bad type")

    with pytest.raises(TypeError):
        broken()

    assert "TypeError" in _all()[1].message


def test_track_step_error_warn_includes_exception_message():
    w = ObservationWriter("comp")

    @track_step(w)
    def broken():
        raise ValueError("specific message")

    with pytest.raises(ValueError):
        broken()

    assert "specific message" in _all()[1].message


def test_track_step_error_warn_has_error_tag():
    w = ObservationWriter("comp")

    @track_step(w)
    def broken():
        raise Exception("x")

    with pytest.raises(Exception):
        broken()

    assert "error" in _all()[1].tags


def test_track_step_error_warn_has_step_tag():
    w = ObservationWriter("comp")

    @track_step(w)
    def broken():
        raise Exception("x")

    with pytest.raises(Exception):
        broken()

    assert "step" in _all()[1].tags


def test_track_step_error_warn_includes_timing():
    w = ObservationWriter("comp")

    @track_step(w)
    def broken():
        raise Exception("x")

    with pytest.raises(Exception):
        broken()

    assert "ms" in _all()[1].message


# ---------------------------------------------------------------------------
# track_step — log_errors=False
# ---------------------------------------------------------------------------

def test_track_step_no_log_errors_still_reraises():
    w = ObservationWriter("comp")

    @track_step(w, log_errors=False)
    def broken():
        raise ValueError("still raises")

    with pytest.raises(ValueError):
        broken()


def test_track_step_no_log_errors_emits_only_entry():
    w = ObservationWriter("comp")

    @track_step(w, log_errors=False)
    def broken():
        raise RuntimeError("quiet")

    with pytest.raises(RuntimeError):
        broken()

    recorded = _all()
    assert len(recorded) == 1
    assert isinstance(recorded[0], NoteObs)
    assert "→ broken" in recorded[0].message


# ---------------------------------------------------------------------------
# Multiple writers / isolation
# ---------------------------------------------------------------------------

def test_two_writers_both_write_to_shared_store():
    w1 = ObservationWriter("alpha")
    w2 = ObservationWriter("beta")
    w1.note("from alpha")
    w2.note("from beta")
    tags_list = [set(o.tags) for o in _all()]
    assert any("component:alpha" in t for t in tags_list)
    assert any("component:beta" in t for t in tags_list)


def test_two_writers_do_not_mix_component_tags():
    w1 = ObservationWriter("alpha")
    w2 = ObservationWriter("beta")
    w1.note("a")
    w2.note("b")
    alpha_obs = [o for o in _all() if "component:alpha" in o.tags]
    beta_obs = [o for o in _all() if "component:beta" in o.tags]
    assert len(alpha_obs) == 1
    assert len(beta_obs) == 1


def test_reset_clears_observations_between_writers():
    w = ObservationWriter("comp")
    w.note("before reset")
    obs_mod.reset()
    assert _all() == []
