# Tool capability contract

## Status

These operation names are a proposed framework-neutral API. They are NOT installed MCP methods. Discover actual host tools and bind compatible operations through an adapter. This package includes only the local helpers described at the end. No live archive, Gmail, DNA, FamilySearch, browser or model credentials are bundled.

Use a capability manifest per run: operation, actual adapter/tool, version, available/read-only/write scope, cost, authentication state, limitations. Exposed tool metadata does not prove that an account is authenticated or a collection is accessible.

## Common envelopes

Requests carry `case_id`, `question_id` where relevant, trace ID, input, and expected revision for mutations. Writes/external actions also carry an idempotency key where supported and an authorization reference scoped to the action.

Results carry status (`ok`, `partial`, `empty`, `blocked`, `error`, `pending`), data, provenance, coverage, warnings, actual cost if measured and retry information. Preserve provider error codes. An empty result is scoped to the performed query. Do not collapse blocked/error into empty.

## Operations

| Group / proposed operations | Input -> output | Behaviour |
| --- | --- | --- |
| Case: open_case, query_case, save_checkpoint | Case ID/query or change set -> state/revision | Preserve provenance; reject stale writes; redact sensitive logs. |
| Research: record_search, get_search_coverage | Query/filters/pages/outcome -> search ID or coverage map | Preserve incomplete ranges and access faults. |
| Discovery: discover_repositories, inspect_repository | Context or official URL -> candidate/verified profiles | Use sourced evidence; do not manufacture endpoints. |
| Custody: resolve_record_custody, verify_collection_coverage | Creator/place/period/type -> custodians/holdings/gaps | Separate inference from verified holding statements. |
| Refresh: refresh_repository_profile | Repository ID -> changed endpoints/coverage evidence | Record old route and verification time. |
| Web: search_web, fetch_page | Query/URL -> attributed content and actual fetch status | Search snippets remain leads; respect access controls. |
| Archive: search_catalogue, list_volume_pages, get_record | Repository/collection/query/page -> metadata/images | Use documented interfaces; preserve source reference and pagination. |
| Browser: navigate, inspect_page, capture_page, download_record | URL/observed element -> page/download | Use host-supported automation; do not probe private sessions without site intent. |
| Documents: render_pdf, crop_region, run_ocr, run_htr | Source/page/region/model -> derivative and transform metadata | Preserve originals and coordinates. Recognition output is provisional. |
| Sources: register_source, store_original, link_derivative, build_citation | Source bytes/metadata or parent links -> source/citation IDs | Hash bytes; prevent overwrites; do not infer source independence from hashes. |
| Evidence: add_observation, attach_locator, record_conflict | Cited statement/locator -> observation/conflict IDs | Require source/locator; retain ambiguity and literal wording. |
| Identity: find_candidates, compare_timelines, propose_merge | Mentions/person IDs -> transparent comparison/proposal | Matching tools propose; evidence review decides. Merges must be reversible. |
| Hypotheses: create_hypothesis, record_support, record_counterevidence, revise_conclusion | Question/observations/rationale -> versioned assessment | Status changes require an argument and dependency handling. |
| Mail: search_mail, read_thread, draft_mail, send_mail, download_attachment | Scoped query/thread/draft/recipient -> verified thread/message/source IDs | Sending only with explicit applicable authorization; reconcile unknown delivery before retry. |
| Review: validate_references, run_case_evaluation | State/result/trace -> errors, scores, limitations | Structural checks do not establish historical truth. |
| Output: render_report, draw_tree, export_gedcom, export_research_bundle | Case/audience/format -> artifact and loss report | Public disclosure is separate from private artifact creation. |

## Connector strategy

Prefer a documented source API when available, then the authorized host browser, then a precise request/onsite handoff. IIIF can expose images, page sequence and metadata; OAI-PMH is metadata harvesting, not automatic full-text/image access. Verify protocol support per repository.

FamilySearch production API access has approval and authentication requirements; possessing a user login does not create an approved API application. Transkribus is an optional external recognition service with its own account/cost conditions. Use current official documentation before implementation. Treat a paywall, missing connector or blocked session as an access constraint, not permission to bypass it.

For Gmail discover actual host tool schemas rather than hardcoding names from another runtime. Search/read/draft/send are distinct capabilities. Use a mock mailbox for evaluation; never test sending against real archives by default.

## Bundled executable helpers

- `scripts/case_tools.py init --case-id ID --question TEXT --out FILE`: create a new portable JSON case, refusing to overwrite.
- `scripts/case_tools.py validate FILE`: check core structure, source/claim links, supported-relationship gates, missing references and cycles.
- `scripts/case_tools.py hash-file FILE`: return SHA-256 and byte size of a supplied file.
- `scripts/gedcom_tools.py check FILE`: pre-import check of a GEDCOM 5.5.1 or 7.0 file for possible duplicates, impossible dates and impossible parent/child ages. Errors are impossible combinations; warnings are doubtful ones. Exits 1 when there are errors. It checks the tree against itself, never against records.
- `scripts/gedcom_tools.py import FILE --out CASE [--question TEXT]`: open a new case from a GEDCOM file, refusing to overwrite. The file is the one source consulted; each fact becomes a cited observation with a provisional conclusion, the tree's own citations are kept on the observations as leads, and each check issue becomes a planned task. Nothing is marked supported. Merging into an existing case is research-maintenance work.
- `scripts/gedcom_tools.py export CASE --out FILE [--report LOSS] [--include provisional]`: write GEDCOM 5.5.1 holding only `supported` and `source_supported` claims (provisional ones only on request, and then labelled), each fact citing its source with the citation locator and text and noting its status. Families never gain a parent whose link was not reviewed. A loss report (default `FILE.loss.json`) counts what was left out and lists people not known to be deceased, to check before sharing. Refuses to overwrite and refuses a case that does not validate.
- `evaluation/genealogy-evaluation/scripts/stage_case.py` (maintainers only, not installed by default): stage public synthetic case inputs and selected runtime skills for a test.
- `evaluation/genealogy-evaluation/scripts/score_result.py` (maintainers only, not installed by default): score a result against starter fixtures; trusted action traces are separate from agent output.

All helpers use Python's standard library and perform no network access or sending. The GEDCOM helper checks, imports and exports; GEDCOM is an exchange view, so the full case stays the record. No PostgreSQL/MCP server, OCR engine, scheduling service or vendor adapter is implemented by this ZIP.

## Failure and retry

Bound retries; retry transient read errors only when useful. On an ambiguous write/send, query the target state using the request key or message/thread metadata before repeating. If the service cannot establish completion, mark uncertain and ask for reconciliation rather than risking a duplicate. Preserve partial findings and exact limitations.
