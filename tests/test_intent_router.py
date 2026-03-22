"""Tests for intent router."""


from src.intent_router import classify_intent_keyword, parse_intent


def test_keyword_status():
    assert classify_intent_keyword("check status") == "status"
    assert classify_intent_keyword("what is the status") == "status"
    assert classify_intent_keyword("where am i") == "status"


def test_keyword_reset():
    assert classify_intent_keyword("reset") == "reset"
    assert classify_intent_keyword("clear state") == "reset"
    assert classify_intent_keyword("start over") == "reset"


def test_keyword_step():
    assert classify_intent_keyword("step") == "step"
    assert classify_intent_keyword("next") == "step"
    assert classify_intent_keyword("single step") == "step"


def test_keyword_resume():
    assert classify_intent_keyword("resume") == "resume"
    assert classify_intent_keyword("continue") == "resume"
    assert classify_intent_keyword("proceed") == "resume"


def test_keyword_run_default():
    assert classify_intent_keyword("run") == "run"
    assert classify_intent_keyword("execute") == "run"
    assert classify_intent_keyword("") == "run"
    assert classify_intent_keyword("something random") == "run"


def test_parse_intent_from_argv():
    assert parse_intent(["cmd", "status"]) == "status"
    assert parse_intent(["cmd", "run", "pipeline"]) == "run"
    assert parse_intent(["cmd"]) == "run"  # default
