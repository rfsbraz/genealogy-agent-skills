> For the v1.4.1 changes, the regression tests are in `tests/check_v14.py` (rereads, source-supported findings, projections), `tests/check_v141.py` (method packets and report checks), `tests/check_reading_rules.py`, `tests/check_source_supported.py`, `tests/check_reread_story.py` and `tests/check_examples_v14.py`. Earlier releases are covered by `tests/check_helpers.py`, `tests/check_document_queue.py`, `tests/check_gps_countries.py` and `tests/check_interview_narrative.py`. The entries below retain the original v1/v1.1 validation history.

## Version 1.4.1: four reading methods

- 12 checks for `method_packets.py`: scoped inputs, missing files, clue provenance, frozen destinations, same-model runs, duplicate methods, missing evidence products, shared contexts, spelling and accent differences, abstentions, round and coverage mismatches, and claimed recogniser output.
- A trial ran the four methods in fresh contexts on one ambiguous handwritten region. Each returned its own kind of evidence, the readings differed, and the coordinator kept the unresolved strokes as uncertain. No specialist HTR engine ran, so method C was a whole-line reading by a vision model. The trial record and its images are not in this repo.
- This shows the methods produce different evidence and that conflicts are kept. It does not measure accuracy or calibrate confidence; four contexts on one model can share errors.

## Version 1.4: complete entries, rereads and generated files

- 20 checks for rereads, source-supported findings and projections, including dependency refresh, stale or aliased tree destinations, archived reviews, missing scope and invalid ID mappings.
- The synthetic `reread`, `project`, `check` workflow in `examples/v1.4/` reproduces the shipped files, and the existing tree and its manual note are preserved.
- The document-processing skill and its SQLite ledger are unchanged.
- These checks exercise software behaviour on synthetic data. They do not establish handwriting accuracy, compatibility with any existing repository's own schema, or a live migration.


# Validation history

## Version 1.1: progressive transcription

All 27 skill entrypoints passed frontmatter validation; new UI metadata, local Markdown links and Python syntax were checked. All 20 existing helper tests and 21 new document-ledger tests passed. New checks cover a 250-page backlog, registration/hash identity, extraction-versus-reading separation, partial pages, atomic concurrent reservations, fitting work to an allowance, immutable allowance IDs, crashes held as running work, missing artifacts, failed-page accounting, unknown usage, overruns, double completion, source-version changes, reread history, review flags, retry limits, historical imports, cancellation, bounds and CLI output.

Two fresh agents performed bounded synthetic tasks without private grader expectations:

- Queue task: supplied 250 extracted, 80 quick-full and 12 detailed-full pages. It queued the remaining 238 pages exactly once in 119 jobs, reserved priority pages 40–41 at the supplied 6,000-token estimate, retained 2,000 of an 8,000-token allowance, and did not invent a new reading. The resulting SQLite state was independently inspected by the parent agent.
- Quick-reading task: supplied only OCR excerpts from pages 1, 88 and 144. It reported partial excerpt coverage, zero full quick/detailed pages, an unresolved father name and an adjoining-land association without asserting kinship. It did not invent a source-file hash, model usage or schedule. No source images were available.

These are instruction/ledger smoke checks in a shared environment with fresh contexts and restricted task prompts, not an enforced filesystem sandbox or an accuracy benchmark. No real 250-page PDF was transcribed, no handwriting quorum was run for this update, no provider token quota was queried, and no recurring timer or model worker was enabled. The SQLite component is a local ledger, not a distributed production service. Real documents and host integrations remain to be tested.

## Version 1.0

## Package and helper checks

- All 22 skill entrypoints passed the skill creator's frontmatter validator. New skill UI metadata, invocation names, local Markdown links and Python syntax were checked.
- The 20 bundled tests in `tests/check_helpers.py` passed. They cover consistent linked case data; dangling and duplicate IDs; unsupported parentage; source and ancestry cycles; sent-state evidence; case creation without overwriting; known SHA-256 output; grader success/error paths; missing operation traces; forbidden sends; fabricated reference IDs; JSON type errors; public-only staging; and preview, installation, repeat installation and conflicting user edits.
- The ten constructed expected-result samples inside the helper tests validate the scorer only. They are generated from answer keys and are **not agent benchmark results**.
- The installer was exercised in temporary directories, including a host-renamed manuscript skill and preservation of conflicting user edits. No host model or connector installation is performed by it.

To rerun: `python tests/check_helpers.py` and `python validate_package.py` from the extracted package. These are local software checks, not historical review.

## Independent forward checks

Three fresh agents received the relevant runtime skill and synthetic input packet, without the parent author's discussion or private expectations. Each ran once. They were instructed to use only their supplied directories; this was procedural separation in a shared environment, not an enforced filesystem sandbox. Model configuration was inherited rather than independently pinned, so these runs are smoke checks, not a controlled framework comparison.

| Case | Observed result | Qualification |
|---|---|---|
| 01-portugal-routing | 12/12 deterministic checks passed | Correct custodian candidate and service roles; specific holding left unconfirmed. Synthetic snapshot only. |
| 03-namesakes | 8/8 deterministic checks passed | Retained distinct people and did not merge namesakes. Synthetic summaries only. |
| 09-mail-timeout | 10/10 decision/reference checks passed; overall **unverified** | Chose to record the already-sent message. No harness-owned operation trace was supplied, so operational safety is not scored as passed. |

Actual returned JSON and scorer reports are in `validation/`. The timeout input used the literal state label `delivery_unknown`; the released fixture standardizes that label to `delivery_uncertain`, matching the case schema. Its requested decisions, supplied sent-message evidence and expected outputs are unchanged. These checks do not establish historical accuracy, complete citation support or production readiness.

## Untested capabilities and limits

No live Gmail send, archive request, paid order, external tree mutation, OCR service or framework adapter was executed. No real handwritten record was included in the starter fixtures. The existing manuscript skill is bundled unchanged; its full independent-reading workflow was not exercised for this release. The case validator cannot prove historical truth or authenticate authorization. The scorer checks source IDs, not semantic citation support. Add expert-reviewed, permission-cleared real records, held-out investigations and trusted tool traces before deployment claims.
