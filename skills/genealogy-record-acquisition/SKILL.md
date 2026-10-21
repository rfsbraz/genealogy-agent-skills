---
name: genealogy-record-acquisition
description: "Use when genealogy-mode or the user needs a record downloaded, browsed page by page or ordered, with provenance kept. Not for deciding which collection to search."
disable-model-invocation: true
---

# Acquire and Preserve Records

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task.

## Inputs

Planned action; verified record/collection reference; access route; permissions; existing source IDs and hashes.

## Procedure

1. Confirm the intended document, collection dates and custodian. Inspect actual permissions and available access; do not bypass sign-in or restrictions. Use official/documented acquisition routes.
2. Preserve available original bytes before processing. Record URL, access timestamp, archival reference, page/folio, entry, creator, custodian, filename and checksum when computable. A checksum identifies bytes, not authenticity.
3. Capture all pages needed for context: headings, pagination, continuation, margins, endorsements and signatures. Preserve sequence and distinguish page-image index from original foliation.
4. When browsing, log the exact volumes/pages/date intervals examined and any missing, unreadable or blocked pages. A partially searched volume stays partial.
5. Register crops, OCR and translations as derivatives linked to the source. Never alter or overwrite the original; retain transform/model metadata for interpretation.
6. If only a catalogue entry or index can be accessed, preserve it as the source actually consulted and mark the original unavailable. Route a specific information/reproduction request to archive-correspondence or an onsite brief to archive-fieldwork.
7. Check the acquired material matches the requested item and is legible enough for the question. Report missing pages and technical faults; retry only where a different route can help.
8. Return the source package and checkpoint acquisition before analysis. Record the checkpoint as a document version in the genealogy-document-processing queue (`register` with the computed hash and inspected page count). If the queue is not available, or the host keeps its canonical record as text, write the same fields (source ID, location, SHA-256, page count, access date) to the host's own source record and say the queue was not used. Do not infer family identity from a matching filename or search hit.

## Output contract

Preserved source package; citations and hashes; page/coverage log; access limitations; extraction packet or specific acquisition request.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Never describe an inaccessible image as inspected. Do not invent image contents from catalogue metadata. Do not send enquiries or incur charges without applicable authorization.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Browser/download; PDF/image inspection; file storage; checksum helper; mail attachment retrieval; optional IIIF.

## Handoffs

Handwriting -> genealogy-read-manuscripts; text -> evidence-extraction; missing records -> correspondence/fieldwork.

## Example

A certificate PDF has a reverse-page annotation. Acquire and cite both pages before extracting the birth and subsequent marriage information.
