# Score Commit Unit

Score a **functional** commit unit on quality dimensions (0-10 scale).

## Input Fields

- `commit_log`: The LLM-regenerated commit log (what changed, in Chinese)
- `module`: The detected module
- `files`: Files changed
- `diff_chunks`: Code diff snippets (up to 50 lines each)

## Scoring Dimensions

Score each unit on three dimensions and average:

1. **Clarity** (0-10): How clear is the description?
   - 8-10: Specific function/class/action named
   - 5-7: Describes what changed but not specifically how
   - 0-4: Vague ("update", "fix stuff")

2. **Domain Fit** (0-10): Does it map to a clear domain/module?
   - 8-10: Module clearly identified, affects core domain logic
   - 5-7: Module identified, affects supporting code
   - 0-4: No clear module, or affects infrastructure only

3. **Reusability** (0-10): Is the change reusable/generalizable?
   - 8-10: Adds a reusable abstraction, utility, or pattern
   - 5-7: Feature with some reusable parts
   - 0-4: One-off fix or feature

## Output Format

```yaml
score: <integer 0-10>
breakdown:
  clarity: <0-10>
  domain_fit: <0-10>
  reusability: <0-10>
justification: One sentence explaining the score
```

## Examples

```
Input:
  commit_log: "在 parser 中新增 parse 函数用于 DSL 解析"
  module: parser
  files: [src/parser.py]

Output:
  score: 9
  breakdown:
    clarity: 9
    domain_fit: 9
    reusability: 8
  justification: "Clear function name, core parser domain, reusable DSL parsing utility"

Input:
  commit_log: "修复边界条件"
  module: unknown
  files: [src/utils.py]

Output:
  score: 4
  breakdown:
    clarity: 3
    domain_fit: 3
    reusability: 5
  justification: "Vague description, no module identified, one-off fix"
```
