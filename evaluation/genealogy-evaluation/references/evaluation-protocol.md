# Measuring a genealogy agent

## Layers

1. Structural tests: schemas, references, state transitions, duplicate keys, dependency cycles, permission and retry handling. These verify software consistency, not historical conclusions.
2. Controlled skill tasks: known packets with independent annotations. Include uncertain and contradictory evidence, indexes, derivative sources, missing volumes, namesakes, shifting jurisdictions and migration.
3. Complete investigations: permission-cleared cases with expert-reviewed evidence and acceptable unresolved outcomes. Score the complete chain from question through source acquisition to conclusions.
4. Live trials: real repositories and tools with bounded scope and an authorization ledger. Record retrieval dates, outages, content changes and human effort. Compare separately from fixed-snapshot benchmarks.

The ten bundled synthetic tasks are starter development fixtures only. They do not test real paleography, live country discovery, Gmail execution or archive access. Add held-out, permission-cleared cases from varied countries, periods, languages and document types. Split by family and collection to reduce leakage. Keep calibration cases separate from final evaluation.

## Scorecard

| Measure | Definition and interpretation |
|---|---|
| Case success | Fully met case rubric / all attempted cases; show failed, blocked and unverified counts separately. |
| Accepted relationship precision | Expert-confirmed accepted edges / all accepted edges. A false accepted parent matters more than a cautious unresolved edge. |
| Relationship recall | Correct recovered edges / expert-established target edges within supplied scope. Do not invent an exhaustive truth set for open research. |
| Claim support | Claims judged supported by their cited evidence / factual claims evaluated. Also report citation coverage separately. |
| Discovery precision | Relevant, verified holdings or repositories / candidates returned. A famous archive name alone is not a verified holding. |
| Discovery coverage | Required known source families or jurisdictions found / those in a reviewed case rubric. Open-web recall has no knowable complete denominator. |
| Identity errors | False merges and false splits, each with counts and eligible decisions. Do not hide these in a combined score. |
| Uncertainty handling | Appropriate unresolved outcomes / cases requiring abstention; evaluate missed solvable cases as well. |
| Operational reliability | Correct, evidenced state transitions / attempted operations; include timeouts, retries, resumed runs and idempotency failures. |
| Efficiency | Tokens, tool charges, latency and human review minutes per attempted case and per successful case. Include failed attempt costs. |
| Critical failures | Fabricated evidence, unsupported accepted parentage, destructive false merges, unauthorized external actions. Report count and rate separately; these block release under a chosen policy. |

If probabilities are emitted, evaluate calibration against independently adjudicated outcomes using a proper scoring rule such as Brier score; do not mistake self-reported confidence for calibration. Cite sample size. Use confidence intervals or paired bootstrap comparisons for larger datasets; the ten starter cases cannot establish broad performance.

## Framework comparisons

Pin model/version, inference settings where available, skill content hash, tool adapter versions, sources, context, token/time budget, retry limit and permissions. Reset caches, case ledger and fixture mailbox between attempts. Run each configuration repeatedly, preferably paired on the same case snapshots. State variation and all exclusions. A framework change bundled with a model change is a system comparison, not an isolated framework comparison.

Use ablations: baseline model and tools; add skills; add checkpointing; add independent review. Test failures injected at acquisition, parsing, tool timeout, authentication and message reconciliation. Capture harness-owned traces. Do not issue real emails or paid requests in routine regression tests.

Deterministic checks handle exact fields and operations. Blinded human genealogical review handles evidence sufficiency and ambiguous evidence. A model judge can assist narrative rubric scoring but should be calibrated against human judgments and must not be the sole judge of its own output. Reward defensible alternative paths and justified abstention.

## Release decisions

Set targets before running, based on intended use. For an initial release, require no observed critical failures and complete provenance for accepted conclusions, then describe the remaining evidence base honestly. These are chosen gates, not industry certification. A small zero-failure sample is weak evidence about rare failures. Maintain a regression set and a genuinely held-out set; tune only against the former.

## Framework adapters

Any agent framework can use the public input/result contract. An adapter needs: fresh state creation, skill mounting, controlled tools, agent execution, result capture, harness trace capture, budget accounting and evaluator invocation. Optional external projects include Inspect AI, Promptfoo, LangSmith and Phoenix; consult their current official documentation before integration. This distribution includes no installed adapter for them.
