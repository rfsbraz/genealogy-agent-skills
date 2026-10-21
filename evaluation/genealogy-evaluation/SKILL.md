---
name: genealogy-evaluation
description: "Design and score reproducible genealogy-agent evaluations across models, skills and frameworks. Use to benchmark research quality, compare configurations, assess regressions or validate changes to this skill suite."
---

# Evaluate Genealogy Agents

Read the [shared research contract](../../skills/genealogy-mode/references/shared-contract.md) and [data model](../../skills/genealogy-mode/references/data-model.md) before writing case state. When this skill is installed next to the runtime skills, both files are in the sibling genealogy-mode skill. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../../skills/genealogy-mode/references/gps-policy.md), [easy-use rules](../../skills/genealogy-mode/references/easy-use.md), [revisions and projections](../../skills/genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../../skills/genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Agent configurations; controlled task dataset; independently checked expectations; tool fixtures; budget; permissions; model/framework versions.

## Procedure

1. Read references/evaluation-protocol.md and references/result-contract.md. Select skill-level, complete-investigation or live tests. Use the bundled synthetic cases only as starter regression fixtures, not evidence of real genealogical competence.
2. Keep test expectations and evaluator notes outside agent-visible mounts. Stage only public task/source files and the skills actually under test. The same-host staging helper provides convenience, not filesystem isolation.
3. Use an independently reviewed answer key with supported, rejected and legitimately unresolved outcomes. Add real permission-cleared documents and handwriting cases with expert-reviewed readings before making deployment claims.
4. Hold the model, skill version, tools, scope, data snapshot and budgets equivalent when comparing frameworks. Change one factor for ablations. Reset case and mailbox state; separate paired repeatable tests from live web trials.
5. Run multiple independent attempts and retain every result, failure and cost. Record external tool execution in a harness-owned trace. Never grade authorization or delivery from an agent’s self-report alone.
6. Use deterministic checks for IDs, values, citations, state and tool outcomes; human review for historical validity and ambiguous readings; calibrated model judges only for appropriate rubric items. Allow alternative valid research paths.
7. Report case success, accepted-relationship precision/recall, citation coverage/support, verified source discovery, uncertainty handling, operational reliability and total cost per success. Denominators and excluded/unverified cases must be explicit.
8. Treat fabricated evidence, unsupported accepted parentage, destructive false merges and unauthorized external actions as critical failures. Do not average them away. Zero observed failures in a small suite does not establish zero risk.
9. Preserve held-out cases by family/collection and keep grading feedback out of agent inputs. Use failures to develop new regression tests; refresh a held-out set if tuned against repeatedly.
10. Record observed results separately from planned targets. Use scripts/score_result.py for starter checks and scripts/stage_case.py for public fixture staging. Framework adapters, real mail/search services and model calls must be supplied by the host.

## Output contract

Versioned benchmark; per-case scores and failure classes; actual execution traces; comparison report with cost/variation; next improvements.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Never describe synthetic regression passes as live archive or handwriting validation. Do not use a self-written answer as a claimed agent run. Keep private answer keys out of installed runtime context for evaluated agents.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Bundled stdlib scorer/stager; optional Inspect AI, Promptfoo, LangSmith or tracing platform; isolated fixture tools and independent reviewer.

## Handoffs

Use failures to revise the relevant skill; rerun changed behaviour and required regression gates; orchestrator documents measured limitations.

## Example

Compare the same model with and without identity-resolution on namesake cases. Count all attempts and report false accepted links separately from abstentions.

## Bundled resources

- [evaluation-protocol.md](references/evaluation-protocol.md)
- [result-contract.md](references/result-contract.md)
- [score_result.py](scripts/score_result.py)
- [stage_case.py](scripts/stage_case.py)
- [Benchmark catalogue](assets/benchmark/catalogue.json): the case list. Public inputs live in `assets/benchmark/public/` and grader answer keys in `assets/benchmark/answer-keys/`; keep the answer keys outside agent-visible mounts.

## Ease of use

Apply [ease-of-use.md](references/ease-of-use.md) alongside evidence quality: measure time to a useful first action, unnecessary questions, successful resumption and user understanding. Test short answers on difficult evidence so brevity never hides a conflict. Code checks and synthetic agent trials do not establish real-user accessibility.
