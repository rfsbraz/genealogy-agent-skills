---
name: genealogy-identity-resolution
description: "Determine whether historical record mentions refer to the same person and manage competing candidates. Use for common names, aliases, migration, conflicting ages, duplicate profiles or proposed merges."
disable-model-invocation: true
---

# Resolve Person Identities

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Person mentions; candidate persons; cited timelines; geographic and naming context; uncertainty and conflicting evidence.

## Procedure

1. Build a candidate table from all plausible identities, retaining an unknown alternative. Preserve separate IDs; normalization aids matching but never overwrites original names.
2. Compare age intervals, family relationships, spouses, residences, occupations, signatures, witnesses, institutions and migration chronology. Explain agreement and disagreement for each candidate.
3. Weight evidence by relevance, reliability and independence rather than counting matches. Repeated indexes or online trees derived from the same document add no independent support.
4. Test chronological and geographic feasibility with explicit assumptions. Distinguish an unusual event from a contradiction; avoid unsupported biological or travel impossibility rules.
5. Investigate disconfirming records and alternatives. Consider namesakes, remarriage, reused infant names, aliases, informant errors, boundary changes and multiple households.
6. State whether mentions can be linked, remain candidates, or must be kept distinct. Tie the decision to observations and a written rationale. An apparently exact name/date match can remain ambiguous.
7. Propose a merge only after evidence review. Use a reversible mapping that preserves original IDs, assertions and provenance; record what changes and the ability to undo it. Update dependencies rather than deleting inconvenient evidence.
8. Route consequential uncertainty to proof-evaluation and independent-review. If unresolved, specify the record most likely to distinguish candidates.

## Output contract

Candidate matrix; proposed mention-person links; identity conclusion/status; merge or separation proposal; disconfirming evidence and next test.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Never auto-merge on fuzzy name similarity alone. Do not interpret two differently named records as separate people solely because surnames differ. Preserve unresolved links outside accepted tree relationships.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Timeline/query tools; transparent candidate matching; source-dependence graph; reversible change ledger.

## Handoffs

Planner pursues discriminating sources; proof/review assesses the conclusion; maintenance applies authorized reversible updates.

## Example

Two men share name and village but have distinct spouses and contemporaneous children. Keep separate candidates and investigate further instead of attaching both families to one person.
