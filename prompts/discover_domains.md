Given the following semantic units from a codebase's git history, cluster them into core domains.

Units summary:
{units_summary}

Architecture document (if available):
{architecture_content}

Requirements:
1. Each domain must have: domain (short identifier), description (one sentence), paths (associated directory prefixes), keywords (associated keywords)
2. Target 5-15 domains, maximum 20. If fewer than 5 natural domains exist, output the actual count. If more than 20, merge similar domains until under 20.
3. Cluster based on semantic content (themes, operations, summaries), not just directory structure
4. Output a JSON array only, no explanation
