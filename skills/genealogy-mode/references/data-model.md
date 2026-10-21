# Evidence-centred data model

## Design

Use stable project-scoped IDs, not names as keys. The JSON case is the portable interchange/checkpoint; a host may implement the same concepts in SQLite, PostgreSQL or another store. This package does not supply a production database, authentication server or synchronization service.

Preserve raw values and interpretations separately. Empty, unknown, illegible and absent are different states. Dates may be exact, ranges, before/after, approximate, reported age or unresolved literal strings. Keep historical place labels and jurisdiction intervals.

## Entities

| Entity | Required meaning and minimum content |
| --- | --- |
| Case | ID, goal, revision, active question, questions, work state, authority scope, provenance and history. |
| Question | ID, precise question, person/mention scope, places/periods, work status and success/stop conditions. |
| Person | ID, display label and optional attributes supported through observations/conclusions. Names do not define identity. |
| Mention | ID, literal name/role, source and locator. A record occurrence that may or may not be linked to a Person. |
| Relationship | ID, from/to persons, typed relationship, date scope, claim status and conclusion ID. |
| Event | ID, event type, literal/normalized date/place, participating mention/person roles and observation IDs. |
| Place | ID, literal/normalized names, candidate identities, historical jurisdictions with dates, precision and sources. |
| Source | ID, source actually used, title, creator/custodian, type, URI/reference, access date, file/hash and derivative parents. |
| Citation | ID, source ID, exact page/folio/entry/region/timestamp locator, optional quotation and access context. |
| Observation | ID, source/citation/locator, literal statement, subject mention/person, predicate/value, interpretation and uncertainty. |
| Hypothesis | ID, question, candidate explanation, supporting/opposing observations, discriminating searches and status. |
| Conclusion | ID, question, claim, status, observation IDs, rationale, conflicts addressed, limits and dependencies. |
| SearchAttempt | ID, question, source/collection, query/method, names/filters, dates/pages examined, gaps, time and outcome. |
| ResearchTask | ID, question, action/rationale, dependencies, target, work status, result IDs and restart conditions. |
| Repository | ID, roles, aliases, official URLs, historical/current jurisdiction, creator relationships and verification evidence. |
| Holding | ID, repository ID, creator, fonds/series/reference, date/place scope, gaps, access modes and verification evidence. |
| Correspondence | ID, request key, recipient verification, authority reference, thread/message IDs, state, costs, attachments and follow-up. |
| Change | ID, revision, time/actor, affected IDs, old/new status or patch, rationale, sources and reversibility. |

The machine schema is assets/case.schema.json. The local validator enforces its documented core invariants and references, not every domain rule or historical fact. Additional descriptive fields are allowed; keep cross-entity links explicit and stable.

## Claim provenance

Use a claim chain: source -> citation/locator -> observation -> conclusion -> relationship/tree view. Do not link a supported relationship only to a website homepage. An observation can faithfully transcribe an inaccurate assertion; the conclusion must assess its accuracy.

An observation's `uncertainty` describes the extraction or interpretation. A conclusion's `status` describes the claim. A task's `status` describes progress. Never use one as a substitute for another.

Represent competing identities as multiple person/mention candidates. A `same_person` conclusion or reversible identity mapping records a linkage decision; retain all original mention IDs. Avoid in-place merges that destroy the ability to undo an error.

## Date object

```json
{
  "literal": "aged about forty",
  "kind": "estimated_range",
  "calendar": "unknown",
  "earliest": null,
  "latest": null,
  "method": "Do not calculate until the event date and age convention are known",
  "uncertainty": "approximate reported age"
}
```

Keep date order/calendar ambiguous when appropriate. Store a derived range only with the method and assumptions; do not turn reported ages into exact birthdays.

## Repository access and search coverage

Access modes include description, name_index, digital_images, request, onsite, restricted and unknown. These are independent: a description may exist without images or an index. Verify access per holding, not for the repository as a whole.

Search outcomes include found, no_match, partial, inaccessible, technical_failure and not_attempted. Record exact coverage and gaps. `no_match` means only that the documented search found no match; further reasoning is needed before using absence as evidence.

## Changes and concurrency

Before a mutation read the current revision. Use an expected revision check, a transaction/lock appropriate to the backing store and an append-only change history. The supplied CLI is a file helper, not a concurrent store. Hosts implementing multi-writer access must add locking/transactions.

On conclusion revision, traverse `depends_on` and mark affected descendants for review. Preserve a rejected or superseded assertion with its prior sources and rationale. Record changes to tree exports separately from source observations.

## Exchange

GEDCOM is an exchange view. `scripts/gedcom_tools.py import` brings a tree in as provisional claims cited to the file, after the `check` pass; see tool-contracts.md. Preserve the complete research record, source dependencies, searches, uncertainty and correspondence in the full case bundle. Generate an export-loss report for each target application's unsupported fields. Verify import/export behaviour on a fixture before using it on important research.

## Document processing ledger

Use genealogy-document-processing for DocumentVersion, ProcessingRun, PageResult, ProcessingJob and BudgetWindow records. Its SQLite ledger tracks source hashes, physical pages, actual methods, artifacts and usage independently of genealogical truth. Observations may reference `processing_run_id` and `source_version_id` plus page/region and artifact hash. These are external ledger references; the case validator does not resolve them. When a host keeps runs in its own record instead of the queue, an observation carries `external_run` (`kind: external`, `ref`) in place of `processing_run_id`. Keep existing source IDs and raw files in their document store. New readings create new run records and trigger review of affected observations/conclusions. Never infer detailed coverage or historical support from a quick index or OCR pass.

## Case schema 1.1 and GPS review

The v1.4 case template emits schema_version `1.2`; the core schema still reads `1.0` and `1.1` for progressive migration. Each supported or definitively rejected conclusion requires `gps_review`, defined in `assets/gps-review.schema.json`, plus full text on every audited citation. The review stores five element assessments, reviewer provenance, alternatives, source/information assessments, conflicts, written reasoning and an evidence digest. See gps-policy.md for lifecycle and validator limits. No person-level confidence flag substitutes for this review. Existing 1.0 labels remain attributed legacy assessments until audited; `validate --gps` reports gaps without mutating files.

## v1.4 changes

An observation can have `supersedes: OBSERVATION-ID`. Both readings remain immutable; the current view excludes observations replaced by a later reading. One old observation has at most one successor; correct that successor again to form a chain. Branching alternatives are uncertainty/candidate readings, not two authoritative replacements. Each replacement retains source, citation, run/version and the reason. See [revisions-and-projections.md](revisions-and-projections.md).

`source_supported` conclusions carry a scoped `evidence_assessment`. They are distinct from both unassessed leads and full-review `supported` conclusions. Relationships may use the same labelled working status. A changed reading leaves old conclusion evidence references intact and flags reassessment; the researcher must explicitly reassess the new observation rather than silently replacing a premise.

Choose one authority per project. The bundled projector makes case-canonical private facts and tree notes deterministically, with only ID/path mapping in its configuration. Generated files must not be hand-maintained. An existing repository can instead remain canonical with the case as an interchange view, through an adapter that follows [host-adapter.md](host-adapter.md); the bundled projector is not an automatic importer or a live repository migration.
