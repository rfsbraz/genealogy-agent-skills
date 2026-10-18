# Processing model and scheduling policy

## Independent dimensions

- Mode: `extract` (machine extraction), `quick` (one bounded reading), `detailed` (evidence-controlled reading for its declared scope).
- Per-page scope: `full`, `partial`, `failed`. Inspect blanks before marking full. Honest illegibility can remain in a full-scope transcription.
- Method: actual engine/visual method, model, skill revision, reader/round counts and limitations. Distinguish sequential detail from a blind quorum.
- Review flag: unresolved material uncertainty, disagreement, contamination or changed evidence. Coverage does not remove this flag.
- Historical conclusion: maintained by the evidence model, never inferred from processing level.

A file can have 250 extracted pages, 80 quick-full and 12 detailed-full pages. These sets overlap. Display them separately with exact page lists. Abstracts are partial reading coverage. No OCR match is not proof of absence.

## Identity and history

Keep document/source IDs stable. Each immutable version has SHA-256, physical page count and locator. Registration can compute a local file hash; hashes supplied by an external document store are marked reported. Remote bytes are not verified by this CLI. Re-registering a document/hash is idempotent; changing its page count is an error. A version can also be a set of page images: each image keeps its own hash per page, the version hash is computed from the ordered image hashes, and the hash method is `manifest_computed` or `manifest_reported` (cli.md, Register a set of page images).

Every run stores one version/mode, page outcomes, method metadata, folio/region notes, artifact paths/hashes, times, flags and measured/estimated usage. Keep prior outputs immutable. Stored hashes expose drift but cannot restore overwritten text; the host must preserve versions.

Existing `data/facts/<DOC-ID>.json` can cite `processing_run_id`, `source_version_id`, page/region and artifact hash. Historical transcriptions can be imported only after their actual scope/method are established and explicitly labelled imported. Do not claim reading a transcription file performed its original transcription, or invent an independent quorum for a single-pass reading.

## Queue policy

Prioritize active-question evidence, disputed names/kinship, damaged text, margins and uncertain boundaries. Then cover remaining pages in stable order. Allocate regular capacity to older low-priority work. Full-document detail should attempt every page, while preserving inaccessible/illegible outcomes honestly.

Job identity includes source version, mode and pages. Planning excludes existing full coverage and queued/running work. Partial/failed work requires re-planning; after the configured attempt limit it requires an explicit reread reason. Forced rereads are new runs, never overwritten results. Prefer focused rereads over recurring full-volume rereads.

## Budget and crashes

The host grants a named non-overlapping UTC allowance window, daily or aligned with actual provider resets. Never infer reset timing from a subscription label. Estimates include input, output, image and all reader calls as accounted by the host. Currency and token limits are distinct.

`claim` reserves estimated tokens in an SQLite transaction. Workers sharing this ledger share claims and allowance. `finish` releases reservations and charges actual usage; unknown usage charges the estimate and remains labelled estimated. Record overruns honestly and block later claims if exhausted. Only the host/provider can enforce the external hard cap.

Remaining context length, idle time and ChatGPT plan access are not quota APIs. No allowance window means no claim. Multiple independent ledgers require an external shared budget allocator.

A crashed worker keeps its running job and reservation. Reconcile before finishing it as failed/partial with accounted usage. There is deliberately no automatic lease reclamation that could duplicate model calls. Re-plan after settling. Back up SQLite using its backup API or export a consistent snapshot; do not copy active database files without transaction state. `restore` rebuilds an empty database from such an export. A host whose canonical record is text can keep the export as the versioned record and the SQLite file as a rebuildable cache (cli.md, Host-canonical mode). This local ledger is not a multi-host distributed queue.

## Host timer contract

Each tick: obtain allowance -> claim fitting work -> execute appropriate skill -> persist artifacts -> settle results -> flag affected evidence -> checkpoint. Stop on exhaustion, cancellation or concrete blockers. A timer may invoke this every few hours, but work requires source access, permission, allowance and a real worker.
