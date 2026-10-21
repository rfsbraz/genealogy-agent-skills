---
name: genealogy-case-intake
description: "Use when genealogy-mode hands off a new case, an imported tree or a new collection: audits starting evidence and sets research questions. Not for opening a case, which genealogy-mode does."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Genealogy Case Intake

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

For a conversational start, route to genealogy-interview. Reuse its cited testimony and provisional seed; do not repeat the interview. Intake audits the result and existing imports.

## Inputs

Goal; family tree or GEDCOM if supplied; documents; testimony; previous reports and searches; existing identifiers and permissions.

## Procedure

1. Inventory supplied artifacts and their origin without altering originals. Record missing attachments and files mentioned but not actually available.
2. Reuse the user’s stated goal. Ask only if a useful next action is blocked; accept incomplete information and keep to one short question at a time. Identify whether the goal concerns: identity, relationship, event, descendants or life history. Convert the goal into dated and localized questions. Continue useful inventory work before asking a necessary clarification.
3. Separate user testimony, imported assertions, actual source statements and previous conclusions. Importing a tree does not make its relationships supported. Preserve previous IDs and cite the imported tree as the source actually consulted.
4. Build a starting timeline with date ranges and source references. Keep event date separate from registration date, baptism from birth, and address from birthplace. Identify ambiguities in person identity before attaching imported records.
5. Identify unsupported links, contradictory dates, duplicate candidates and gaps. Do not merge candidates during intake. Record privacy/sharing preferences and existing communication or purchase authority.
6. Review previous search logs and correspondence. Record coverage, pending requests and reasons to repeat a search; avoid spending the same effort blindly.
7. Choose the most useful first question and create a checkpoint. State what is known, reported, inferred and unknown, with dependencies on uncertain readings.

## Output contract

Case brief; artifact inventory; initial persons and mentions; questions; timeline; prior-work audit; scope and authority record.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not generate a complete ancestry from surname matches or copied trees. If the user supplies a correction, preserve the old assertion in history and revise its status; do not erase its provenance.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

File inspection; GEDCOM importer when available; case store; email search only within the requested research context.

## Handoffs

Send setting questions to locality-research, origin clues to origin-source-discovery, unsupported links to the planner, and imported contradictions to identity-resolution.

## Example

An imported tree identifies a grandfather without citations. Preserve the relationship as provisional and make parentage a question rather than treating it as the starting truth.
