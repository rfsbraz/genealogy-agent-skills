# Source registry and tree gap finder

The gap finder (`scripts/gap_finder.py`) reads the people in a case and lists the records that should exist for them, with the sources that should hold those records. It reads, ranks and explains. It never searches, orders, writes to archives or changes the case. Standard library only, no network.

Contents: registry files; gap finder modes; ranking and approval; searches already done; learning from searches; limits.

## Registry files

One JSON file per country, checked against `assets/source-registry.schema.json` (start from `assets/source-registry-template.json`). Keep the files in a folder and pass it with `--registry`. `validate-registry PATH` checks a file or a folder.

- `place_names`: names that identify the country inside a place literal. A case place can also carry `country` with the registry `code`.
- `sources[]`: one entry per source or series.
  - `record_types`: birth, baptism, marriage, death, burial, census, foundling, newspaper, probate, military, migration, other.
  - `coverage[]`: `from_year`, `to_year` (null for open) and `places` (`*` for every place). Each range can narrow `record_types`.
  - `access`: `route` (online_images, online_index, catalogue_only, request, onsite) and `cost` (free, account, paid).
  - `query`: `method` (catalogue_search, index_search, browse_by_book, order_certificate, onsite_visit, write_to_custodian) and `how`, one plain sentence.
  - `known_gaps[]`: record types, places and years the source does not cover, with a `note`. Learned gaps also carry `learned_from` (the search ID) and `learned_on`.
  - `verification`: how and when the coverage was checked. Record it for every real country; coverage is a claim about the source, not about a person.

No real country ships yet. Add one only with coverage checked against the custodian's own pages; the country starting points in genealogy-origin-source-discovery are the place to find those custodians.

## Gap finder modes

`gaps CASE --registry DIR [--person ID] [--mode detail|expand] [--json]`

- `detail` (detail a person): a missing or unsourced birth or baptism; a death or burial, when there is a death fact or the person was born more than 110 years ago; a marriage for each couple without a sourced marriage. A fact counts as sourced when a supported or source_supported conclusion uses it.
- `expand` (expand a node): for a person with no parents in the case, the baptism and marriage records that usually name parents; for each couple, the children's baptisms or births over the mother's and father's fertile years (15 to 50), listing the children already known. Siblings come from the parents' couple search.

Years come from the facts, widened by 5 years for approximate dates, or are estimated from children, spouses and marriages. A candidate without a year or a place with a registry is listed under `skipped` with the reason.

## Ranking and approval

Expanding to parents ranks highest (a generation gained), then children, then detail. A free online source adds to the rank, and a candidate whose only sources are paid ranks lower. Each source says why it matches (record type, place and years), how to query it and its cost. Paid sources carry `needs_approval: true`: ask the user before ordering, and never order on the strength of this list.

## Searches already done

A search in the case marks a source as done for a candidate when it has `source_id`, `record_types`, `person_ids` and `years`, its outcome is `no_match` or `found`, and its years cover the candidate's. That source is then left out and listed under `already_searched`, so a negative search is not repeated. A `partial`, `inaccessible` or `technical_failure` search keeps the source and appears under `earlier_attempts`. Absence of a record is still not evidence until the coverage is assessed.

## Learning from searches

When a search shows that a source lacks part of its stated coverage, record it on the search as `coverage_gap` (`record_types`, `places`, `from_year`, `to_year`, `note`), then run `learn CASE --registry DIR --search ID`. It adds the gap to that source's `known_gaps` once, with `learned_from`, and later gap lists skip that source there and then. A plain `no_match` teaches nothing: it says the person was not found, not that the records are missing.

## Limits

The registry describes sources, not people. A match means a record may be there, not that it exists. Identity, kinship and proof stay with identity-resolution, family-reconstruction and proof-evaluation.
