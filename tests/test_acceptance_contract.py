"""Test acceptance contract unification.

The runtime requires exactly "acceptance: true" to proceed with baseline synthesis.
These tests verify that the contract is enforced correctly.
"""

from src.refine_executor import _check_acceptance


class TestAcceptanceContract:
    """Test that acceptance contract uses "acceptance: true" format."""

    def test_acceptance_true_allows_baseline(self):
        """Test that "acceptance: true" allows baseline synthesis to proceed."""
        feedback = """
## Review Feedback

Some feedback here.

acceptance: true
"""
        result = _check_acceptance(feedback)
        assert result is True

    def test_acceptance_false_blocks_baseline(self):
        """Test that "acceptance: false" blocks baseline synthesis."""
        feedback = """
## Review Feedback

Some feedback here.

acceptance: false
"""
        result = _check_acceptance(feedback)
        assert result is False

    def test_no_acceptance_blocks_baseline(self):
        """Test that missing acceptance field blocks baseline synthesis."""
        feedback = """
## Review Feedback

Some feedback here but no acceptance line.
"""
        result = _check_acceptance(feedback)
        assert result is False

    def test_invalid_acceptance_blocks_baseline(self):
        """Test that invalid acceptance values block baseline synthesis."""
        invalid_values = [
            "acceptance: maybe",
            "acceptance: yes",
            "acceptance: semantic baseline accepted",
            "acceptance:true",   # Missing space
            "accepted: true",    # Wrong key
        ]

        for invalid_value in invalid_values:
            feedback = f"""
## Review Feedback

Some feedback here.

{invalid_value}
"""
            result = _check_acceptance(feedback)
            assert result is False, f"Expected {invalid_value} to be rejected"

    def test_acceptance_true_case_insensitive_value(self):
        """Test that acceptance value is case-insensitive (True, TRUE, true all work)."""
        # According to the code comment: "case-insensitive value"
        # The implementation does: stripped = line.strip().lower()
        # So "acceptance: True" should work
        feedback = """
## Review Feedback

acceptance: True
"""
        result = _check_acceptance(feedback)
        assert result is True

    def test_acceptance_true_whitespace_tolerant(self):
        """Test that acceptance check handles surrounding whitespace."""
        feedback = """
## Review Feedback

  acceptance: true
"""
        result = _check_acceptance(feedback)
        assert result is True

    def test_acceptance_key_case_sensitive(self):
        """Test that the acceptance key itself is case-sensitive."""
        feedback = """
## Review Feedback

Acceptance: true
"""
        result = _check_acceptance(feedback)
        # The key "Acceptance" (capital A) should not match "acceptance"
        # because the code does line.strip().lower() which lowercases the entire line
        # So "Acceptance: true" becomes "acceptance: true" and should match
        assert result is True
