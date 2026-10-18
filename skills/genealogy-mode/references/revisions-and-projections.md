# Corrections, findings and generated repository files

## One editable authority

Choose the canonical evidence store before writing. For a new case, the case JSON owns observations, identities, conclusions and search history. Generate `data/facts/<DOC-ID>.json` and `data/tree-notes.json` from it. With an explicit tree mapping, also generate a copy of `data/tree.json` with research notes. These are private build outputs: change the case, then rebuild. Do not ask the agent to maintain three editable versions of every finding.

For an established repository that remains canonical, keep editing its existing model and derive a temporary case interchange view. Do not introduce an independently maintained case mirror. The repository's adapter follows the [host adapter contract](host-adapter.md): what export must produce, what import must accept, where working case state lives, and the round trip check. The generic projector is not a repository importer, merger or publishing tool. Before adopting case-canonical mode, map every legacy fact/person ID once, preserve manual notes, review native schemas and validate the staged diff. No live repository migration is bundled or implied.

SQLite remains the processing ledger: source versions, runs, jobs, coverage and budgets are unchanged. Case JSON owns genealogical assertions; a processing run owns how the image was read. Link actual run IDs rather than copying the ledger into the case. A host whose canonical record is text can version the queue's JSON export and rebuild the SQLite file from it with `restore` (genealogy-document-processing references/cli.md, Host-canonical mode).

## Reread an already processed passage

1. Locate the source version and original pixels. Use the ledger's existing `plan --reread-reason` for pages already covered. Read the entire target entry's relevant fields, continuation and margins. For handwriting, apply four methods in separate contexts; the same model is allowed. Record actual isolation and method execution.
2. Freeze the new reading before revealing the old interpretation to any blind reader. Save the transcript and complete its real processing run. Compare the frozen result against the earlier text.
3. Prepare one replacement observation for each corrected assertion. Give it a new stable ID, the same source ID, its citation/locator, statement, uncertainty, optional structured value, actual new `processing_run_id`, and known `source_version_id`. Add the run's `reading_method` block (genealogy-read-manuscripts references/protocol.md) so the observation records how it was read. Do not invent run IDs to satisfy validation. If no queue run exists because the host keeps the run in its own record, give `external_run` instead, for example `{"ref": "host-ledger:entry-0042", "system": "host text ledger"}`, or pass `--external-run host-ledger:entry-0042`. Give one or the other, never both. If the earlier run is unknown, retain that fact; do not backfill it speculatively.
4. Record the correction:

```bash
python genealogy.py reread case.json --old O-OLD --reading replacement.json --reason "Wider scan makes the final digit legible" --actor "actual-reader-id" --expected-revision 4
```

This command records a completed reading; it does not transcribe, create a ledger run or invoke a model. An external run is saved on the new observation and its change entry as `external_run` with `kind: external`, and projected fact rows carry it too. The helper does not check that the host reference exists. A reread with no run reference at all still fails, and a second external reread needs a new `ref`. It appends the new observation with `supersedes`, retaining old text. Its change entry records the reason, actor, old claim/review snapshots and affected IDs. Conclusion evidence references stay unchanged until the researcher reassesses them. Dependent conclusions and relationships return to provisional/review-required; affected events are flagged. The case-wide GPS digest also invalidates other ready reviews; these are listed separately from dependencies of the corrected text.

5. Reassess the new observation, affected hypotheses, identity mappings, events and claims. Add support/counterevidence explicitly; clear review-required flags only after that work. Restore `source_supported` with a current scoped assessment, or `supported` with the full review. Rebuild projections and stories.

The helper uses an expected revision, local lock and atomic file replacement. Repeating an identical correction ID/input is a no-op; reusing its ID for different input fails. A second correction must supersede the current observation, never create a competing authoritative branch. The new schema version is 1.2; old case schemas remain readable. Only one observation is replaced per invocation; a multi-assertion correction requires a sequence of calls using the returned revisions. A crashed lock must be reconciled before manual removal. These are local-file guarantees, not a distributed transaction with SQLite.

## Useful findings before full proof

`source_supported` means the cited evidence has been assessed for a specific scope. Record a small `evidence_assessment` with `basis`, `scope`, `reviewer`, `reviewed_on` (YYYY-MM-DD), `known_conflicts` and `limitations`. Use an empty conflict list only after actually checking the consulted evidence. Each conflict object contains `description`, `material`, `resolved`, and `reason`; an unresolved material conflict prevents this status. The validator also requires full citations, current observations and assessed dependencies.

The report should say what is established: for example, “The marriage entry names Manuel as her father; cross-record identity remains open.” It should not call that a fully proved parentage linkage. Use `provisional` for an unassessed hypothesis, `unresolved` for an open conflict, and `supported` only with a current full GPS review. Detailed reading and agreement between reading methods do not themselves establish any genealogical claim status.

## Build private facts and tree notes

```bash
python genealogy.py project case.json --out build/private-v1
python genealogy.py project case.json --mapping repository-map.json --tree existing-tree.json --out build/private-v2
```

The destination must be new. Generation validates the case first and leaves inputs untouched. Values, uncertainty, citations and statuses come from the case, with no manually repeated finding text in the mapping. Generated fact rows include `id`, `person`, `mention_id`, `role`, `field`, `value`, `evidence_class`, `location`, `note`, `uncertainty`, source/citation/run references and `supersedes`, plus `reading_method` when the observation has one. Only current observations appear; history stays in the case. Unresolved identity mappings remain null, never resolved by name matching. Each file declares the canonical case ID, revision and digest.

Tree notes include the claim, status, rationale, cited observations and review flag. Notes based on replaced readings remain explicitly flagged until reassessed. A note belongs to each directly associated person, including both ends of an explicit relationship. Conclusions without a person association are listed in `projection-report.json`, not silently lost. This helper does not infer ancestry edges or prune existing tree relationships.

Optional mapping example:

```json
{
  "documents": {"S-1": "DOC-001"},
  "persons": {"P-1": "existing-person-slug"},
  "tree_person_pointers": {"P-1": "/people/0"},
  "tree_notes_field": "research_notes"
}
```

`documents` selects safe output filenames; several source assets may map to one document. `persons` maps stable IDs one-to-one. When supplying a tree, `tree_person_pointers` must identify every case person's exact object in that supplied snapshot. Confirm identity before supplying the pointer; a schema check cannot prove who it refers to. Regeneration replaces only notes tagged `generated_by: genealogy-case` for this case. Other notes and fields are preserved. An existing non-list notes field causes an error; choose a compatible separate field or implement the repository's adapter rather than overwriting it.

The generated envelope is `genealogy-private-projection/1.0`. Confirm native schema compatibility before copying into an existing project; extend its build adapter once where necessary. Additional custom fields stay in the canonical case; these views are not a lossless backup. The output is private and can contain living-person data. Publishing is a separate, authorized build with its own selection policy.
