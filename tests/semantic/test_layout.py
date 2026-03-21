from pathlib import Path


def test_trigger_prompt_exists():
    path = Path(__file__).parents[2] / "prompts" / "semantic" / "trigger.prompt.md"
    assert path.exists()

def test_runner_exists():
    path = Path(__file__).parents[2] / "src" / "semantic" / "run.py"
    assert path.exists()
