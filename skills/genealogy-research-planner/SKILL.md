---
name: genealogy-research-planner
description: "Use when genealogy-mode or the user needs the next search chosen, competing explanations tested or a stalled case unblocked. Not for running the searches themselves."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Plan Genealogy Research

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Active question; existing observations and conclusions; candidate identities; source portfolios; coverage/search log; access and budget constraints.

## Procedure

1. State the question precisely and list plausible explanations, including an unknown/unresolved option. Separate identity uncertainty from uncertainty about an event or relationship.
2. For each explanation state what observations would support or contradict it. Identify which available sources can distinguish the explanations rather than merely repeat known names.
3. Review already searched collections and exact coverage. Do not repeat a search unless the date range, query, index, source access or interpretation has materially changed.
4. Rank actions qualitatively by discriminating value, expected information, independence, access, effort and dependencies. Record the rationale; avoid pseudo-precise probability scores.
5. Specify each action: target creator/collection; names and variants; period; locality; search/browse method; expected clue; stopping condition; result categories; fallback.
6. Plan bounded batches. After findings, update hypotheses and the next action. Read enough surrounding material to establish context when necessary without expanding into unrelated family branches.
7. If stalled, audit assumptions, original readings, locality, custody, naming variants, collateral relatives and source gaps. Seek an original behind an index, browse unindexed pages, inspect witnesses and neighbours, or search destination records for origins.
8. If no useful feasible action remains, record what prevents resolution and what new evidence would restart it. Distinguish a budget pause from a conclusion that reasonably exhaustive research has been reached.

## Output contract

Ordered action list; hypothesis tests; coverage gaps; alternative strategy; explicit stop/restart conditions.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not reward volume of searches or number of ancestors. Do not assume age estimates or repeated online trees outweigh better evidence. A broad goal does not authorize spending or contacting people.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Case and search ledger; source/repository portfolios; optional estimates of actual tool cost and available budget.

## Handoffs

Acquisition executes actions; discovery fills source gaps; proof-evaluation assesses whether remaining searches matter to a conclusion.

## Example

After three name searches fail, inspect index coverage and the parish register itself, or pursue the person’s marriage, rather than repeat the same name query.

## Bundled resources

- [research-plan-template.md](assets/research-plan-template.md)

## GPS coverage and a manageable plan

Keep the full question-specific source/coverage plan in the case. Show the user only the next best action and, when helpful, two alternatives. In the coverage assessment record jurisdiction, period, record family, completed searches, gaps and why further avenues matter. Choose sources for their ability to distinguish hypotheses, not a fixed document count. A short displayed plan never limits the research necessary for a sound conclusion. Read the coordinator’s gps-policy.md before proposing that a question is resolved.
