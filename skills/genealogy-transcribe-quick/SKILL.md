---
name: genealogy-transcribe-quick
description: "Use when genealogy-mode or the user wants a fast first reading of a long document for searchable text and leads. Not for consequential readings, which need transcribe-detailed."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Quick Document Reading

Read the [shared contract](../genealogy-mode/references/shared-contract.md) and [processing protocol](../genealogy-document-processing/references/processing-protocol.md). Use this deliberate lightweight workflow when the user asks for a quick pass; route consequential uncertain handwriting to genealogy-transcribe-detailed. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md) and [easy-use rules](../genealogy-mode/references/easy-use.md); read them when the task touches them.

## Inputs

Document/source ID, immutable version/hash, original file or verified external reference, physical page count, current coverage, active question, output language and host budget. Do not load a 250-page file into one context.

## Procedure

1. Register the exact version with genealogy-document-processing and verify access. Use physical PDF page numbers starting at one; record printed folios separately. Count covers, inserts, blanks and reverses; never assume PDF page equals folio.
2. Inspect layout and available text. Extract embedded text or use an available OCR/HTR service when justified. Record the actual engine and output. Extraction alone is mode `extract`; it is not a completed quick or detailed reading.
3. Work in bounded page batches suited to layout and host limits. Start with contents/index pages and useful structural samples, but mark unsampled pages unread. An index search cannot establish absence from the full file.
4. For quick transcription, make a bounded reading sweep over each selected entry, including its end, continuation, headings and marginal notes. Finding the requested name or date does not complete the sweep. One pass is a budget choice, not a first-hit stopping rule. Use extracted text as an aid; inspect source images where available, especially names, relationships, dates, amounts and negations. Record whether the method was OCR-only, text-layer review or visual reading. Never imply visual verification of pages not viewed.
5. Preserve literal wording, page boundaries and uncertainty using `[?]`, `[ilegível]` or the requested language's equivalent. Mark intentional omissions. Keep summaries and extracted entities separate from transcription. If only abstracts were produced, label them abstracts and record partial coverage.
6. Complete the field checklist below before stopping a target entry. Produce a compact document map, available transcription, source-located leads and a detailed-reading queue. Prioritize material kinship statements, ambiguous identities, uncertain names/dates, marginalia, damaged text and pages needed for the active question.
7. Record every processed page's coverage, method, artifacts and actual usage through the ledger. Use partial/failed status for unfinished pages and exact regions for selected passages. A full quick pass means the entire page was processed at that level, not that every word is certain.
8. Save full outputs privately and show a concise overview by default. Return page numbers and a link/path to longer text. Do not paste a 250-page transcript into chat unless requested.

## Output and gates

Return an immutable quick-run artifact, per-page results, section map, provisional leads with locators, unresolved readings, detailed-reading tasks and actual processing metadata. A lead can guide research; consequential uncertain readings need closer examination before accepted identity/parentage claims.

Keep unread, illegible, blank and searched-with-no-match distinct. Only mark blank after inspection. Do not claim a blind quorum in quick mode or fill text from genealogical expectations. If access, language or OCR is inadequate, record the limitation and queue appropriate work.

Send selected originals to genealogy-transcribe-detailed, keeping quick outputs out of initial blind-reader packets. Schedule remaining work through genealogy-document-processing; never invent a scheduler or quota API.

## Target-entry completion checklist

Capture the main finding and every visible field that could change identity or the answer: all principals, ages, parents and their stated status, spouse/partner, residence/origin, occupation, witnesses or informants, event and registration dates, signatures, negations, amendments and margins. For a marriage, check both spouses and both sets of parents, even if the first matching spouse answers the initial query. Distinguish `read`, `not stated after inspection`, `illegible`, `outside scope`, and `not yet inspected` per relevant field. Do not turn omitted or unread material into absence.

A quick pass is complete for its declared target when its boundaries and fields have been swept, the answer has locators, and uncertainties or unfinished continuation are queued. It need not transcribe unrelated entries or read the whole volume. A budget interruption gives `partial` and the exact restart location. Known uncertainty in a crucial parent/name/age routes to detailed reading before promotion.
