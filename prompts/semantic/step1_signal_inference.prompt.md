Goal:
Convert fact-layer inputs into `signals.yaml`.

Pipeline:
- program: normalize inputs
- model: infer fact clusters and implicit semantic signals
- program: validate schema and write canonical YAML

Output groups:
- domain_signals
- concept_signals
- rule_signals
- demand_pattern_signals
