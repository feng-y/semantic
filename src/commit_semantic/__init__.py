"""
Commit semantic extraction module.

.. deprecated::
   The old extract/generate/export pipeline is deprecated.
   Use ``skills/commit-extract/`` and ``skills/commit-semantic/`` instead,
   which follow the Team Agent architecture (SKILL.md + prompts/*.md + Task tool).
   Only ``git_utils`` is still used by the new skills.
"""

from .git_utils import get_commit_details, get_commit_list

__all__ = [
    'get_commit_list',
    'get_commit_details',
]
