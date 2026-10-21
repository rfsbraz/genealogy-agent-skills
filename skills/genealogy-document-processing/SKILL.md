---
name: genealogy-document-processing
description: "Use when genealogy-mode or the user needs a page ledger or rereading queue for long or interrupted documents under a token budget. Not for reading the handwriting itself."
license: MIT
compatibility: "Python 3.10+ for the ledger CLI, which uses SQLite from the standard library."
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Document Processing Ledger

Read [processing-protocol.md](references/processing-protocol.md) and [cli.md](references/cli.md). Use [document_queue.py](scripts/document_queue.py) for a local SQLite ledger. It does not call a model or run a timer; the host supplies access, readers, budget telemetry and periodic invocation.

## Procedure

1. Register stable source/document IDs, exact version hash, page count and locator. When the source is served as separate page images, register them as one version with an ordered image list, so each page keeps its own image hash. Leave originals in their repository or document store; the ledger stores references and processing history. Keep private material out of public builds.
2. Track extraction, quick and detailed reading separately, per physical page and immutable version. Preserve folio labels in results. Never infer full-file reading from sampling or an index.
3. Queue bounded quick work for orientation. Queue detail for material evidence and uncertainty, then progressively cover remaining pages if full detail is the goal. Estimate tokens from host telemetry or a measured sample, including reader fan-out.
4. On a host timer, read an explicitly granted allowance window. Reserve capacity transactionally before claiming work. If no job fits, wait for a new allocation or deliberately split queued work; do not exceed the budget to fill idle time.
5. Dispatch to genealogy-transcribe-quick or genealogy-transcribe-detailed. Persist job/run IDs and source version. Capture execution and usage through the host where possible.
6. Finish with page-level full/partial/failed results, method metadata, artifact hashes and usage. Missing telemetry provisionally charges the reservation and is labelled estimated, never zero. The host enforces provider hard caps and monetary limits.
7. Re-plan missing coverage after partial/failed attempts with a retry bound and recovery reason. After a crash, reconcile artifacts, provider usage and worker state before settling the running job. Do not automatically release held reservations or duplicate uncertain work.
8. Retain all runs. A new source hash creates a new version; old readings do not count toward it. Summaries use the current version only. Reordered scans require explicit page mapping before reuse.
9. Link changed readings to the evidence layer and queue reassessment. Never promote parentage from processing level alone. Reuse existing source/person IDs rather than creating a second family tree.
10. Report exact page coverage, review flags and backlog. Mode counts overlap; do not sum them as distinct pages. Export JSON for audit/Git, keeping the mutable SQLite ledger private and out of Git unless binary snapshots are deliberately managed. Use `restore` to rebuild a database from an export; a host whose canonical record is text follows the host-canonical section of cli.md.

## Output and limits

Return the ledger, versioned history, coverage, artifacts, jobs, reservations, usage and restart/review handoffs. The CLI reserves a host-supplied allowance, not ChatGPT subscription quota. It cannot discover spare tokens, access a document store, transcribe, enforce a provider cap or schedule itself.

[schedule.example.json](assets/schedule.example.json) is inactive configuration. Install a host runner and timer before describing the routine as live.
