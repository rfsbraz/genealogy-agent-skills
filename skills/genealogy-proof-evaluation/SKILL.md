---
name: genealogy-proof-evaluation
description: "Use when genealogy-mode or the user must judge whether an identity, parentage, event or origin claim meets the evidence standard. Not for gathering more records."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Evaluate Genealogical Proof

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

Read the coordinator’s [GPS policy](../genealogy-mode/references/gps-policy.md) before evaluating a claim.

## Inputs

Focused question; hypotheses; observations and actual sources; provenance/dependence; search coverage; conflicts; proposed conclusion.

## Procedure

1. Restate the precise claim and alternatives. Determine what evidence is necessary to distinguish them and which material is actually available.
2. Assess the search’s breadth for this question: relevant original or best available sources, known gaps, indirect evidence, collateral research and feasible unexplored avenues. Do not treat a time limit as reasonably exhaustive research.
3. Verify citations identify the sources actually consulted and precise locations. Inspect consequential source passages; citations to inaccessible originals must be attributed through the derivative used.
4. Evaluate creator/informant context, proximity to the event, possible motives/errors, independence and the information’s relevance. Avoid blanket reliability ranks for entire record classes.
5. Correlate the timeline and identity/relationship evidence. Explain contradictory observations individually; do not choose the most convenient date or silently drop an inconvenient source.
6. Distinguish a negative search from negative evidence. Use an absence only when an expected record/statement, surviving coverage and search adequacy justify the inference, with competing explanations considered.
7. Write a concise argument sized to the problem. Use a statement for a simple uncontested claim, a summary for several sources, and a fuller argument for indirect or conflicting evidence.
8. Complete a claim-level `gps_review` covering all five elements, using the coordinator’s template and schema. Include alternative hypotheses, counterevidence, citation text, source/informant assessments, information quality and unresolved gaps. Run the strict case validator before assigning supported or definitively rejected. For a useful bounded finding without a full review, use source_supported with the scoped evidence_assessment in the GPS policy; for unassessed or materially unresolved claims use provisional or unresolved. Preserve superseded decisions with reasons. Support applies to this claim, not every field of the person. New contrary evidence can reopen it.
9. State residual limitations and the next evidence that could change the conclusion. Send disputed consequential claims for independent review when feasible.

## Output contract

Written proof assessment and structured five-element GPS review bound to the evidence digest; claim status; source and conflict audit; remaining research and reopening conditions.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

No majority voting over documents or agents. Do not issue calibrated percentages without a validated model. Direct evidence is not synonymous with accurate evidence. Unresolved is a valid result.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Source inspection; evidence/citation graph; search coverage; comparisons and audit logs.

## Handoffs

Planner resolves remaining gaps; independent-review challenges arguments; maintenance records conclusion revisions; reporting communicates them.

## Example

Three websites repeat one index. Treat them as one dependency chain and seek the underlying record or independent evidence before accepting parentage.
