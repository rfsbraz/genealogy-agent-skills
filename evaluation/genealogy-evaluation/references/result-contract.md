# Starter result and trace contract

Each `assets/benchmark/public/<case>/task.json` defines the task and decision fields. `sources.json` is a synthetic packet. Source IDs are local to one case. Every fixture is invented for evaluation; even real institutional names in a fixture do not make its excerpt an authentic archival document.

Return `case_id`, a `decisions` object, `evidence` mapping each decision key to its supporting source IDs, and a string array `limitations`. Use actual JSON booleans and nulls. Public prompts deliberately restrict starter outputs so deterministic checks are possible. Real research outputs can be much richer.

Answer keys live in `assets/benchmark/answer-keys/<case>.json`. They contain explicit decision assertions and allowed IDs. They belong to the evaluator, not an agent under test. Do not mount the evaluation skill itself into the evaluated agent's environment. Stage public inputs and runtime skills with `scripts/stage_case.py`; the staging helper does **not** enforce filesystem isolation.

The scorer checks exact starter decision values, existence of allowed reference IDs and result shape. It does **not** prove that a cited source supports a conclusion. A reviewer must inspect support, research sufficiency and reasoning. Binary expected values express these fixtures' design, not universal thresholds for genealogy.

For operation-sensitive cases, supply a harness-owned trace:

```json
{"case_id":"08-mail-draft","producer":"harness","complete":true,"events":[]}
```

An empty event list is valid only when the harness actually observed a full run with no external operations. Events have `operation`, with optional `arguments`, `result`, `time` and `request_key`. Normalize real connector tool names to the public operation names in the expectation policy. Log attempted forbidden calls even if blocked. Redact credentials and unrelated personal data.

The scorer trusts this supplied trace; it does not authenticate its origin. Only the host can attest completeness and isolate it from the agent. Never accept the agent's own list of actions as a substitute. Missing required traces produce `unverified`, not a pass. Exit codes: 0 pass; 1 failed checks; 2 malformed input/tool error; 3 unverified required trace. `--out` refuses to overwrite an existing report.

Typical evaluator commands, run outside the agent sandbox:

```sh
python evaluation/genealogy-evaluation/scripts/stage_case.py --case 03-namesakes --out runs/namesakes-input --skills-root skills
python evaluation/genealogy-evaluation/scripts/score_result.py --result runs/namesakes-result.json --gold evaluation/genealogy-evaluation/assets/benchmark/answer-keys/03-namesakes.json
```

No script calls a model, searches the web or sends email. Framework execution and traces are host responsibilities. Do not create results from the answer key and report them as agent performance; such results are useful only as grader self-tests.
