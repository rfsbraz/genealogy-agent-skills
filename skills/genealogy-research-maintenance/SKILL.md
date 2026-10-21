---
name: genealogy-research-maintenance
description: "Use when genealogy-mode or the user needs case evidence kept consistent after discoveries, merges, imports or corrections. Not for planning the next search."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Maintain Research State

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Current case revision; proposed change set; observations and source IDs; affected conclusions; target export or tree.

## Procedure

1. Read the latest authoritative case and expected revision. Reject a stale write and reconcile against the current version; never overwrite concurrent work silently.
2. Validate IDs, references, source locators, conclusion dependencies and status values before writing. Use the shared schema and bundled structural checker; semantic review remains necessary.
3. Apply changes as a reversible, attributed change set. Preserve originals, previous assertions, rejected hypotheses and superseded conclusions. Distinguish corrections of transcription from changes of historical interpretation.
4. On changed identity or relationship evidence, find dependent conclusions and mark them for review. Do not propagate a corrected fact into unrelated persons by name alone.
5. Keep source bytes separate from analysis and derivatives. Preserve hashes and transform metadata; detect duplicate files without assuming byte differences mean independent evidence.
6. Maintain research actions, coverage, requests, hypotheses and restart instructions. Checkpoint before/after external actions to prevent replay after interruptions.
7. For a tree/export, include only intended statuses, preserve identifiers and citations, and generate a loss report for unsupported fields. Keep uncertain links visibly tentative rather than silently exporting them as facts.
8. Summarize what changed, why, the evidence, affected records and remaining inconsistencies. Back up through the project’s authorized storage/versioning system; never publish private research merely to create a backup.

## Output contract

Validated case revision; change log; dependency-review queue; checkpoint; synchronization/export loss report.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Avoid destructive merges and unsupported promotion of claims. Structured validation checks consistency, not genealogical truth. Never claim a push or sync succeeded without its result.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Case/file store, structural validator, hashes, version control, optional tree/export adapters.

## Handoffs

Proof and identity skills authorize scientific status changes; reporting explains revisions; orchestrator resumes from the checkpoint.

## Example

A parent identification is withdrawn. Retain the old argument as superseded, mark dependent ancestry for review, and remove the unsupported edge from the accepted tree view.

## GPS review freshness

Run strict case validation before producing an accepted-claims view. Preserve an old GPS assessment in change history when evidence or identity mappings change; recompute the case evidence digest and reassess affected conclusions. The bundled digest is conservatively case-wide, so any evidence-graph change invalidates all ready reviews until revisited. Operational checkpoint, task and correspondence updates alone do not. A prior supported label without a current review must be shown as review pending, never silently certified by import.

## v1.4 correction and projection entry points

Use the coordinator's scripts/research_updates.py and references/revisions-and-projections.md for `reread` and `project`. A reread appends a new observation with `supersedes`, retains earlier text and reviews, and flags dependent claims/relationships/events. Reassess them before restoring source_supported/supported status. The existing case-wide digest also invalidates other ready GPS reviews, recorded separately from directly affected claims.

For case-canonical projects, regenerate facts and tree notes; never hand-copy the same finding into case JSON, facts and tree JSON. Generate in a new directory, review the diff, and adopt through the project's normal build. Keep repository-canonical projects under their existing authority until a reviewed adapter/migration is available. SQLite scheduling and budget handling are unchanged.
