"""Regression tests for semantic runner next mode finalize guard.

These tests verify that the verify_first guard works correctly in next mode,
preventing the bypass that was possible before the fix.
"""

from pathlib import Path
import tempfile
import yaml
import pytest

from src.semantic.run import main, load_state, save_state, next_stage


def test_next_mode_blocks_when_verify_first_exists_no_evidence():
    """Regression: next mode must block finalize when verify_first exists but no evidence-checks.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Setup: review-decisions with verify_first
        decisions = {
            'domains': [{
                'id': 'review_domain_1',
                'name': 'Test Domain',
                'final_action': 'verify_first',
                'final_reason': 'Needs verification',
                'source_recommendation_id': 'rec_1',
                'evidence_refs': []
            }],
            'concepts': [],
            'rules': [],
            'demand_models': []
        }
        (workspace / 'review-decisions.yaml').write_text(yaml.dump(decisions))

        # Setup: run-state showing step4 complete
        state = {
            'mode': 'next',
            'current_stage': 'step4_review',
            'completed_stages': ['step1_signals', 'step2_candidates', 'step3_recommend', 'step4_review'],
            'artifacts': {},
            'errors': [],
            'warnings': [],
            'blocked_reason': None
        }
        state_path = workspace / 'run-state.yaml'
        state_path.write_text(yaml.dump(state))

        # Execute: should block
        import sys
        sys.argv = ['run.py', 'next', '--semantic-root', str(workspace), '--workspace', str(workspace)]

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert str(exc_info.value) == 'BLOCKED'

        # Verify: state updated with blocked reason
        final_state = yaml.safe_load(state_path.read_text())
        assert final_state['blocked_reason'] == 'verify_first exists but evidence-checks.yaml is missing'


def test_next_mode_blocks_when_evidence_pending():
    """Regression: next mode must block finalize when evidence checks are pending."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Setup: review-decisions with verify_first
        decisions = {
            'domains': [{
                'id': 'review_domain_1',
                'name': 'Test Domain',
                'final_action': 'verify_first',
                'final_reason': 'Needs verification',
                'source_recommendation_id': 'rec_1',
                'evidence_refs': []
            }],
            'concepts': [],
            'rules': [],
            'demand_models': []
        }
        (workspace / 'review-decisions.yaml').write_text(yaml.dump(decisions))

        # Setup: evidence-checks with pending status
        checks = {
            'evidence_checks': [{
                'id': 'check_1',
                'target_id': 'review_domain_1',
                'target_type': 'domain',
                'target_name': 'Test Domain',
                'reason': 'Needs verification',
                'required_evidence': ['Validate evidence'],
                'status': 'pending'
            }]
        }
        (workspace / 'evidence-checks.yaml').write_text(yaml.dump(checks))

        # Setup: run-state
        state = {
            'mode': 'next',
            'current_stage': 'step4_review',
            'completed_stages': ['step1_signals', 'step2_candidates', 'step3_recommend', 'step4_review'],
            'artifacts': {},
            'errors': [],
            'warnings': [],
            'blocked_reason': None
        }
        state_path = workspace / 'run-state.yaml'
        state_path.write_text(yaml.dump(state))

        # Execute: should block
        import sys
        sys.argv = ['run.py', 'next', '--semantic-root', str(workspace), '--workspace', str(workspace)]

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert str(exc_info.value) == 'BLOCKED'

        # Verify: state updated
        final_state = yaml.safe_load(state_path.read_text())
        assert final_state['blocked_reason'] == 'verify_first items have unresolved evidence checks'


def test_next_mode_allows_finalize_when_evidence_completed():
    """next mode should allow finalize when all evidence checks are completed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Setup: review-decisions with verify_first
        decisions = {
            'domains': [{
                'id': 'review_domain_1',
                'name': 'Test Domain',
                'final_action': 'verify_first',
                'final_reason': 'Needs verification',
                'source_recommendation_id': 'rec_1',
                'evidence_refs': []
            }],
            'concepts': [],
            'rules': [],
            'demand_models': []
        }
        (workspace / 'review-decisions.yaml').write_text(yaml.dump(decisions))

        # Setup: evidence-checks with completed status
        checks = {
            'evidence_checks': [{
                'id': 'check_1',
                'target_id': 'review_domain_1',
                'target_type': 'domain',
                'target_name': 'Test Domain',
                'reason': 'Needs verification',
                'required_evidence': ['Validate evidence'],
                'status': 'completed'  # Resolved!
            }]
        }
        (workspace / 'evidence-checks.yaml').write_text(yaml.dump(checks))

        # Setup: run-state
        state = {
            'mode': 'next',
            'current_stage': 'step4_review',
            'completed_stages': ['step1_signals', 'step2_candidates', 'step3_recommend', 'step4_review'],
            'artifacts': {},
            'errors': [],
            'warnings': [],
            'blocked_reason': None
        }
        state_path = workspace / 'run-state.yaml'
        state_path.write_text(yaml.dump(state))

        # Execute: should NOT block (will complete or fail for other reasons)
        import sys
        sys.argv = ['run.py', 'next', '--semantic-root', str(workspace), '--workspace', str(workspace)]

        # The guard should not block, but the stage itself may fail
        # We just verify the guard doesn't raise BLOCKED
        try:
            main()
        except SystemExit as e:
            # If it exits, it should not be BLOCKED
            assert str(e) != 'BLOCKED', "Guard should not block when evidence is completed"

        # Verify: finalize was attempted (added to completed_stages)
        final_state = yaml.safe_load(state_path.read_text())
        assert 'step5_finalize' in final_state['completed_stages']
        # blocked_reason should not be about verify_first
        if final_state.get('blocked_reason'):
            assert 'verify_first' not in final_state['blocked_reason']
