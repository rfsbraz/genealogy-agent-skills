---
name: genealogy-historical-translation
description: "Translate historical genealogical records while preserving legal, religious and kinship distinctions. Use for unfamiliar languages, abbreviations, historical terminology, calendars or ambiguous relationship terms."
disable-model-invocation: true
---

# Translate Historical Records

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task.

## Inputs

Original text/image and locator; diplomatic transcription if available; language/period/genre; active question; uncertain readings.

## Procedure

1. Preserve original wording, spelling and uncertain spans. Resolve reading problems with genealogy-read-manuscripts before treating a difficult word as a translation issue.
2. Identify language, script, period and genre from evidence. Consult appropriate historical dictionaries, archival glossaries and document examples; cite any external reference actually used.
3. Translate close to the source, retaining names, place forms, titles and kinship/legal terms with material ambiguity. Mark abbreviation expansions, supplied text and alternatives separately.
4. Explain historically specific meanings without importing modern legal assumptions. Distinguish legal parentage, acknowledged parentage, guardianship and household roles where the text permits.
5. Keep date/calendar interpretation separate from translation. Preserve the literal date, calendar, conversion rule and uncertainty. Never silently convert an ambiguous numeric date.
6. Produce a plain-language explanation only as a separate layer. Test consequential terms against context and alternative readings.
7. If competence or source quality is insufficient, mark the limitation and specify what expertise or source view is needed.

## Output contract

Aligned original and translation; glossary/abbreviation notes; alternative meanings; sourced calendar conversions; uncertain spans.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not make the translation more certain than the transcription. A translated assertion remains an assertion by its original informant.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Source viewer; historical dictionaries and glossaries; calendar conversion tools when verified.

## Handoffs

Extraction records translated observations; manuscript skill resolves ink; proof evaluates historical truth.

## Example

A term can mean either a legal dependent or child in this context. Preserve both readings and explain why parentage remains unresolved.
