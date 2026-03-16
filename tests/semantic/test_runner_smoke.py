from pathlib import Path
import yaml

def test_run_state_template_exists():
    path = Path(__file__).parents[2] / "templates" / "semantic" / "run-state.template.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "completed_stages" in data
