Given the following domain list and commit semantic units, classify each unit into the most appropriate domain.

Domain list:
{domains_json}

Units to classify:
{units_json}

Requirements:
1. For each unit output: {"id": "<unit_id>", "domain": "<domain_name>"}
2. domain must be a value from the domain list, or "uncategorized"
3. Judge by semantic content (theme, summary, operation type), not just keywords
4. Output a JSON array only, no explanation
