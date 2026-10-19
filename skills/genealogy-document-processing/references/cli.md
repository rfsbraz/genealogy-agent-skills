# Local ledger CLI

Python 3.10+ and SQLite from the Python standard library suffice. The database contains private research metadata. Commands have no network access, no OCR/model integration, no automatic quota detection and no timer. Use an absolute database path for scheduled host invocations. Exit 0 means the command ran; inspect `status`, since no allowance/no fitting job is a normal idle result. Exit 2 means invalid input or execution error.

Every command and option has `--help`. `register --record`, `finish --result`, `import-run --result` and `restore --from` take a path to a JSON file, or `-` to read the JSON from stdin. Inline JSON is refused with "expected a file path, got inline JSON". A missing or invalid file gives an error that names the argument.

## Register a document

```sh
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite init
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite register --record document.json --file sources/example.pdf
```

Example `document.json`:

```json
{
  "document_id": "DOC-EXAMPLE",
  "source_id": "DOC-EXAMPLE",
  "page_count": 250,
  "location": {"kind": "local", "path": "sources/example.pdf"}
}
```

The helper computes the hash with `--file`. Page count must come from actual inspection or a host document tool; this helper does not parse PDFs. For remote-only records, omit `--file`, provide the real `sha256`, and use a locator such as `{"kind":"document-store","document_id":"123","instance":"private-project"}`. The hash is marked reported. The helper neither connects to the document store nor embeds the document. Do not include credentials or signed URLs in locators.

## Register a set of page images

Many archives serve a book as separate page images rather than one file. Register the set as one version by giving an ordered `images` list instead of `sha256`:

```json
{
  "document_id": "DOC-EXAMPLE-REGISTER",
  "source_id": "DOC-EXAMPLE-REGISTER",
  "location": {"kind": "archive-viewer", "collection": "example-register", "instance": "private-project"},
  "images": [
    {"page": 1, "filename": "img-001.jpg", "sha256": "<64 hex characters>"},
    {"page": 2, "filename": "img-002.jpg", "sha256": "<64 hex characters>"},
    {"page": 3, "locator": "viewer image 3", "sha256": "<64 hex characters>"}
  ]
}
```

```sh
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite register --record register.json
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite register --record register.json --images-dir sources/example-register
```

- `page` must run 1, 2, 3 ... in list order. It is the image's position in the version, not the printed folio; keep folios in page results.
- Each image needs a `filename` or a `locator`. With `--images-dir`, every image needs a `filename`, the helper hashes `<images-dir>/<filename>`, and any supplied `sha256` must match. The version is marked `manifest_computed`. Without it, every image needs its real `sha256` and the version is marked `manifest_reported`.
- `page_count` comes from the number of images. If you also give it, it must match.
- The version hash is the SHA-256 of one line per image in page order, `<page> <lowercase image sha256>` followed by a newline. Filenames and locators are not part of it. For two images this is `sha256("1 <hash 1>\n2 <hash 2>\n")`.
- Registering the same list again is a no-op. Changing any image hash, adding or removing an image, or changing the order creates a new version, and queued jobs on the old version are cancelled as with any new version.
- Each image's hash is stored per page. `claim` returns `source.images` with the page, locator and hash of every assigned page, so the worker can check it is reading the exact image.
- Give either `images` or one `sha256`/`--file`, not both.

Opening a database created before image sets adds the per-page table in place (schema 2); existing rows are kept. Exports now have `schema_version` 2 and a `version_pages` table.

## Plan progressive detail

```sh
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite plan --doc DOC-EXAMPLE --mode detailed --pages 5-8,40 --batch-pages 2 --tokens-per-page 4000 --priority 90
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite plan --doc DOC-EXAMPLE --mode detailed --batch-pages 2 --tokens-per-page 4000 --priority 30
```

The numbers illustrate syntax, not measured costs. Supply estimates from actual usage including all blind readers. The second command queues remaining pages without duplicating pending work or full detail. Default attempt limit is three completed attempts per page/mode; running/queued work is excluded. `--reread-reason "new scan available"` permits an explicit additional attempt even after full coverage/attempt limits. Use a new source version when scan bytes changed. Ordinary planning keeps low-priority job priorities unchanged; to reprioritize/split, cancel a queued job and re-plan its pages. Never cancel a running job blindly.

## Host allowance and execution

```sh
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite budget --id example-day --tokens 20000 --start 2030-01-01T00:00:00Z --end 2030-01-02T00:00:00Z
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite claim --worker reader-1 --mode detailed
```

Use real current window dates and the host's allocated allowance, not the illustrative future dates. Windows cannot overlap or be reset by reusing an ID. A claim transaction reserves the job estimate. Repeated claim calls from a worker with running work return that job's ID without assigning more. Another worker cannot claim the same job. The host must execute the returned job, verify source bytes and produce files before finishing.

Example `result.json` for an assigned page 5:

```json
{
  "metadata": {
    "method": "four_method_panel",
    "skill_version": "1.1.0",
    "rounds": 1,
    "reading_method": {"methods": [
      {"method_id": "A", "context_isolation": "fresh", "context_id": "ctx-example-a", "model_identity": "host-default-unspecified", "execution_kind": "visual_feature_analysis", "status": "completed"},
      {"method_id": "B", "context_isolation": "fresh", "context_id": "ctx-example-b", "model_identity": "host-default-unspecified", "execution_kind": "same_hand_comparison", "status": "abstained"},
      {"method_id": "C", "context_isolation": "fresh", "context_id": "ctx-example-c", "model_identity": "host-default-unspecified", "execution_kind": "vlm_line_reading", "status": "completed"},
      {"method_id": "D", "context_isolation": "fresh", "context_id": "ctx-example-d", "model_identity": "host-default-unspecified", "execution_kind": "contextual_decoding", "status": "completed"}
    ]},
    "limitations": ["One model in four fresh contexts", "No same-hand exemplar for B"]
  },
  "actual_tokens": 3200,
  "artifacts": [{"id":"A1","path":"research/transcriptions/run-unique.md"}],
  "pages": [{"page":5,"coverage":"full","requires_review":true,
             "artifact_id":"A1","locator":"#pdf-page-5","printed_folio":"2v",
             "note":"One name remains uncertain"}]
}
```

```sh
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite finish --job RETURNED_JOB_ID --worker reader-1 --result result.json
```

A detailed run must include `metadata.reading_method`, built from the method reports as described in genealogy-read-manuscripts references/protocol.md (Carry the method record forward). `finish` refuses a detailed run without it, or with an unknown `method_id`, `context_isolation` or `status`. The accepted `method_id` values are `A`, `B`, `C`, `D`, `single`, `blind`, `not_blind` and `context`. Other modes may include the block, and `finish` checks it when present.

Every assigned page must appear once. Full/partial pages require an existing artifact and exact artifact locator. Failed pages require a reason; all-failed runs may have no artifacts. Artifact hashes are computed; supplied hashes, if any, must match. Paths are resolved from the working directory, so absolute paths are preferable for workers.

`actual_tokens: null` means unknown and provisionally charges the reservation as estimated. Record all costs honestly, including failed runs and overruns. Original allowance accounting remains attached to the claimed window. A crash holds the reservation until reconciled. Do not fabricate a result just to free tokens.

## Import prior readings

Use `import-run --doc DOC-EXAMPLE --mode quick --result historical-result.json` with the same result shape plus `metadata.external_run_id` (stable import key) and `metadata.original_read_on` (actual date or `unknown`). Preserve actual method and scope; do not promote OCR to a quick reading, or a single-pass transcript to a blind quorum. The command records import time separately, charges zero new model usage and preserves original reported usage in metadata. A detailed import also needs `metadata.reading_method`; use `unknown` for a context that was not recorded. Reusing the key returns the existing run; corrected imports need a new key. Source-version registration must match the original document.

## Status and export

```sh
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite status --doc DOC-EXAMPLE
python skills/genealogy-document-processing/scripts/document_queue.py --db research/processing.sqlite export --out research/processing-export.json
```

Counts are coverage, not confidence. A later full detailed reading may clear an earlier review flag if it explicitly reports no remaining review need; partial/quick readings cannot clear it. Earlier full coverage remains in history even if a later attempt fails. Inspect latest run metadata when adjudicating conflicts. `pages_with_partial_attempts` is historical, not a count of currently incomplete pages.

Exports use a consistent read transaction and refuse to overwrite an existing file. They are private and contain locations, metadata and result details; apply the project's publication filter before any public view. For live backups use SQLite's backup API. Keep `processing.sqlite` and journal/WAL files out of ordinary Git commits; version intentional JSON exports instead.

## Restore from an export

```sh
python skills/genealogy-document-processing/scripts/document_queue.py --db cache/processing.sqlite restore --from research/processing-export.json
```

`restore` creates the database if it does not exist and loads every table from the export in one transaction: documents, versions, version pages, windows, jobs, runs and page results. It accepts exports with `schema_version` 2, the version `export` writes; re-export an older ledger after opening it with this version to upgrade it. It refuses a database that already holds queue rows, so use a new `--db` path. It also refuses an export with another schema version, missing or extra tables, unknown or missing columns, or broken references, and then leaves the database empty. Exporting the restored database gives the same `tables` as the original export; only `exported_at` differs.

## Host-canonical mode

Some host projects keep their canonical record as text in Git, for example a JSONL ledger that CI rebuilds from scratch and checks. In that case:

- The JSON export is the versioned queue record. Commit it next to the host's own record. The SQLite file is a disposable cache: rebuild it with `restore`, run the queue commands against it, then `export` to a new file and replace the committed export in the same commit as the work it records.
- Do not copy queue rows (versions, runs, page results) into the host's own record. Keep a link instead, such as the queue `version_id` or `run_id`, so the host's recount checks do not change when a document is registered.
- If the host cannot run the queue at all, keep the run in the host's own record and pass it to `reread` as an external run. See the coordinator's references/revisions-and-projections.md.
- Never hand-edit the export. Treat a restore failure as a sign the export was changed outside the queue.
