# Host adapter contract

Contents: [section classes](#section-classes), [the sidecar](#the-sidecar), [export](#export), [import](#import), [round trip check](#round-trip-check), [what stays out](#what-stays-out), [publish build and working trees](#publish-build-and-working-trees), [extending the contract](#extending-the-contract).

Use this when an existing repository stays canonical and the agent works on a case view of it. The host project owns its facts. The adapter is the host's own reviewed code that turns the host record into a case view and takes case changes back. This page says what that adapter must do so a host can build it and test it.

The machine-readable contract is [host-adapter-contract.json](../assets/host-adapter-contract.json) (`genealogy-host-adapter` version 1.0, case schema 1.2). [host_adapter.py](../scripts/host_adapter.py) has split and merge helpers, a sidecar check and a round trip check. `examples/host-adapter` in the suite repository is a small reference adapter on synthetic data.

## Section classes

Every case section has exactly one class:

- **required**: lives in the host record and must come back unchanged through export and import.
- **optional**: the host may store it. If it does not, it lives in the sidecar. Either way it must round trip.
- **sidecar_only**: working case state. It lives only in the sidecar, never in the host record.

| Section | Class | Note |
|---|---|---|
| `schema_version` | required | The adapter writes the case schema version it exports. |
| `case_id` | required | Stable case ID. The adapter keeps the same ID on every export. |
| `revision` | required | Changes only when the host record or the sidecar changes. |
| `goal` | sidecar_only | Working research goal. |
| `active_question_id` | sidecar_only | Points at a question in the sidecar. |
| `authorization` | sidecar_only | What the user allowed in this working case. |
| `checkpoint` | sidecar_only | Next action for the working case. |
| `questions` | sidecar_only | Research questions of the working case. |
| `persons` | required | People the host owns. |
| `mentions` | required | Person mentions in sources. |
| `relationships` | required | Relationships the host owns. |
| `events` | required | Events the host owns. |
| `places` | required | Places the host owns. |
| `sources` | required | Sources the host owns. |
| `citations` | required | Citations the host owns. |
| `observations` | required | Readings, including rereads with supersedes. |
| `hypotheses` | optional | Host stores them, or they go in the sidecar. |
| `conclusions` | required | Conclusions the host owns. |
| `searches` | optional | Includes negative searches. Host or sidecar. |
| `tasks` | optional | Host or sidecar. |
| `repositories` | optional | Host or sidecar. |
| `holdings` | optional | Host or sidecar. |
| `correspondence` | optional | Host or sidecar. |
| `changes` | optional | Reread and correction history. Host or sidecar. |

Fields of a record in a required section round trip with that record, through the host. A field may be split out only when the contract lists it:

| Field | Class | Note |
|---|---|---|
| `conclusions.evidence_assessment` | optional | Scoped assessment for source_supported. Host or sidecar, keyed by conclusion ID. |
| `observations.reading_method` | optional | How the reading was made. Host or sidecar, keyed by observation ID. |

## The sidecar

Working case state that the host does not store goes in one versioned file per case, `research/cases/<case-id>.json` in the host repository. It is checked into git with the host, but it is not part of the host's canonical facts. Its shape:

```json
{
  "format": "genealogy-case-sidecar/1.0",
  "case_id": "C-EXAMPLE",
  "sections": {"questions": [], "searches": []},
  "fields": {"conclusions": {"K1": {"evidence_assessment": {}}}}
}
```

`sections` holds optional and sidecar-only sections. `fields` holds listed optional fields, keyed by section and record ID. A section is in the host or in the sidecar, never both. Check a sidecar with `python scripts/host_adapter.py sidecar-check research/cases/<case-id>.json`.

## Export

Export turns the host record plus the sidecar into one case view.

- Write every section in the table, even when empty, and a valid case: `case_tools.py validate` must pass.
- Keep IDs stable. Use the host's own stable IDs as case IDs, or a fixed one-to-one map that the adapter keeps. Never map by matching names, and never mint new IDs on each export.
- Keep `case_id` the same on every export. Change `revision` only when the host record or the sidecar changes.
- Do not drop fields the host cannot show. If a required field has no home in the host, extend the host first.

## Import

Import takes a changed case view back. The host must accept, through its own reviewed write path:

- new and changed observations, including rereads: the new observation with `supersedes`, while the old one stays;
- conclusions and relationships, including their status, review flags and `evidence_assessment` (in the host or the sidecar);
- every other required section;
- optional sections and fields, into the host if it stores them, otherwise into the sidecar;
- sidecar-only sections, into the sidecar.

Refuse a case whose `case_id` does not belong to the host record. Run the host's own checks after import. If they fail, roll back the whole import, not part of it.

## Round trip check

Export, import that export unchanged, then export again. The two exports must be identical. Run it in the host repository, for example in CI:

```bash
python scripts/host_adapter.py check --export "python adapter.py export" --import "python adapter.py import" --sidecar research/cases/C-EXAMPLE.json
```

The export command prints the case JSON. The import command gets the path to a case JSON file as its last argument. The check reports `round_trip: identical` or the sections that changed, plus any case or sidecar errors, and exits 1 on any problem.

## What stays out

- The case view is never a second editable authority for facts the host owns. Edit a required section only through import into the host, never by hand in a saved case file.
- The sidecar never holds required sections or unlisted fields. `sidecar-check` refuses them.
- Processing runs, versions and page results stay in their own ledger. Observations link to them by ID.
- The bundled projector is not an importer. Generated fact files and tree notes are outputs, not import sources.

## Publish build and working trees

Declare in the adapter whether the host's publish build filters conclusions by status (excludes or visibly labels anything that is not `supported`). When the working tree is also the published tree, that declaration decides whether `source_supported` conclusions may enter the tree; see gps-policy.md. If the adapter does not declare a filter, treat the build as unable to filter and keep `source_supported` out of the tree until `supported`.

## Extending the contract

Add a row to the contract file and to the tables above when the case gains a section or a field that may live outside its record. The tests fail on an unclassified section. A new field on a record in a required section needs no change: it round trips with that record. List it under `fields` only when a host may keep it in the sidecar instead.
