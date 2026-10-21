---
name: genealogy-evidence-extraction
description: "Use when genealogy-mode or the user has new records or transcriptions to turn into cited observations, without deciding identity or kinship. Not for transcribing images."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Extract Genealogical Evidence

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task.

## Inputs

Source IDs; original document or attributed transcription; page/entry/region locators; active questions; transcription and translation limitations.

## Procedure

1. Identify what is actually available: original image, index, derivative transcription, authored narrative or testimony. Read the complete relevant entry and its headings, continuation and margins.
2. Use genealogy-read-manuscripts for handwriting. Preserve the diplomatic transcription; store translation and normalized values separately. Do not convert an uncertain letter or date into a certain database value.
3. Create distinct person mentions before linking to established persons. Extract all pertinent roles, relationships, witnesses, informants, occupations, residence, origin, property and institutional clues.
4. Distinguish event dates from registration/announcement dates and birth from baptism. Preserve literal dates, units, ages and place names; record derived date intervals with method and assumptions.
5. For each observation record its source, exact locator, literal statement, interpretation if any, subject mention, predicate/value, and uncertainty. Identify the informant and basis of knowledge where known; use unknown where the document does not say.
6. Separate source type, information quality and relevance to the research question. A document can contain firsthand and secondhand information together; a direct statement can be wrong.
7. Record contradictions and meaningful omissions as observations for analysis. Do not call a blank field proof without understanding the document’s expected practice and context.
8. Return actionable clues and proposed links, preserving the full evidence needed to challenge them. Route identity and historical truth decisions to the relevant skills.

## Output contract

Observation records; mention IDs; normalized values with provenance; uncertainty ledger; conflicts; leads tied to questions.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Every substantive extracted claim needs a source locator. Do not infer biological parentage merely from household position, adoption terminology or an unspecified parent label.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Document viewer/transcription; extraction schema; case validator; date/place utilities.

## Handoffs

Identity-resolution links mentions; family-reconstruction assesses relationships; historical-translation resolves semantic ambiguity.

## Example

A death record reports age 80. Store the reported age and a derived birth interval with assumptions; do not manufacture an exact birthday.

## Processing provenance

When a source has quick/detailed runs, preserve the exact source version, processing run, page/region and transcript artifact hash used for each observation. Do not silently replace an earlier observation after rereading; record the revision and affected conclusions. Use quick leads to plan searches, and escalate consequential uncertain text before accepting identity or parentage.

## Prepare observations for proof review

Preserve a full `citation.text` and exact locator for each observation used in a conclusion. Keep literal reading, calculation and inference separate. Assess information quality and relevance in relation to the question; preserve unknown informants and source dependence explicitly. See the coordinator’s gps-policy.md for the required review fields. A direct statement of parentage is an observation until identity and the whole evidence have been evaluated.
