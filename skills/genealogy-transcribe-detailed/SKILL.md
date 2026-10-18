---
name: genealogy-transcribe-detailed
description: "Perform and track detailed genealogy transcription of selected pages or regions, applying four distinct handwriting methods in separate contexts, including with the same model. Use for diplomatic readings, consequential ambiguities, and scheduled upgrades from quick transcription."
disable-model-invocation: true
---

# Detailed Document Reading

Read the [shared contract](../genealogy-mode/references/shared-contract.md) and [processing protocol](../genealogy-document-processing/references/processing-protocol.md). Resolve the existing `genealogy-read-manuscripts` skill by its declared name for handwritten material; host folder names may differ.

## Inputs

Exact source version/hash; selected physical pages/regions; original imagery; job; budget reservation; required method. Keep previous readings, open questions and review reasons coordinator-only.

## Procedure

1. Confirm source access, version, selected pages, job ownership and host budget. Process bounded batches, typically one to three dense pages, adjusting to measured cost. Do not promise all 250 pages in one run.
2. Render and inspect the actual source. For handwriting, invoke genealogy-read-manuscripts and preserve its blindness, method bounds, uncertainty gates and stopping rules. For clear print, perform a careful source-checked reading and record that method; do not claim a handwriting quorum ran.
3. Keep quick transcripts, previous detailed readings, extracted family names and earlier conclusions out of initial method-specific context packets. Supply originals and neutral coordinates. Freeze the first reading before comparing with previous outputs. Follow genealogy-read-manuscripts rules for later confirmed clues.
4. Preserve spelling, line structure, insertions, deletions, margins and abbreviations where visible. Keep expansions, translation, normalization and historical interpretation separate. Retain uncertainty when the pixels cannot resolve it.
5. Write a new artifact without overwriting quick or earlier detailed transcripts. Record changed spans and reasons, linking source coordinates and old/new run IDs. A rereading is an interpretation of the same source, not independent historical corroboration.
6. Record full coverage only for pages read in their entirety, including relevant margins. A full diplomatic transcription with marked illegibility can be complete in scope and still require review. A carefully read paragraph remains partial-page coverage.
7. Record actual readers, methods, rounds, model/version where exposed, contamination/fallback limits, usage and artifacts. Put the per-method context, model and status in `metadata.reading_method`, as genealogy-read-manuscripts references/protocol.md describes. If budget ends mid-page, checkpoint partial work, settle usage and queue the remainder. Missing telemetry is unknown usage, not zero usage.
8. Send changed readings to evidence extraction and flag affected observations/conclusions for review. Do not rewrite accepted relationships merely because a transcript changed. Preserve superseded interpretations and dependencies.

## Output and gates

Return diplomatic text for the declared scope, uncertainty annotations, page/region coverage, actual methods, differences, immutable artifact/hash, ledger record and affected-evidence handoff. Show a concise user summary unless full text is requested.

Detailed describes method and scope, not guaranteed correctness. Disclose missing methods and context contamination. Four serial fresh contexts are valid even with the same model; four passes in one inherited context are not a panel, so stop and use the blind plus context double reading from genealogy-read-manuscripts. Agreement alone does not establish accuracy. Conflicting detailed rereadings raise review flags instead of automatically overriding earlier results. Re-read again only for a recorded reason: new imagery, a concrete unresolved span or a planned blinded audit.

Record results through genealogy-document-processing, then route to genealogy-evidence-extraction and genealogy-proof-evaluation. Keep private source text out of public exports and reusable examples.

## Runtime and reread handoff (v1.4)

genealogy-read-manuscripts v1.4.1 assigns four distinct methods to separate fresh contexts. The same model may run all four, concurrently or sequentially. Only inability to create fresh contexts stops the panel; model sameness is not a reason to drop the four-method workflow. Preserve each distinct evidence product and actual context/model/tool metadata; evaluate confidence from evidence, not vote totals.

After freezing a reread, compare it with the old reading. Keep the new transcript/run immutable, then record each changed observation with `genealogy.py reread` (coordinator scripts/research_updates.py). Supply a new observation ID, actual new processing_run_id (or `external_run` when the host keeps the run in its own record and no queue run exists), citation and reason. The helper appends `supersedes`, preserves old text/reviews and flags downstream conclusions, relationships and events. It does not itself inspect images or manufacture run IDs. To inspect already-covered pages, the existing SQLite queue already supports `plan --reread-reason`. See the coordinator's references/revisions-and-projections.md.
