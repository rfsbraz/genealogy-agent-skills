---
name: genealogy-origin-source-discovery
description: "Use when genealogy-mode or the user meets a new birthplace, origin or migration and needs the country's sources mapped. Not for searching a known collection's entries."
disable-model-invocation: true
---

# Discover Sources by Origin

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Person/mention IDs; geographic timeline; origins with supporting sources and status; question; dates; relevant occupation, institutions or documented community affiliations.

## Procedure

1. Load the shared contract and references/country-discovery.md. Separate birth, residence, citizenship, ancestry and transit. Treat uncertain origins as competing branches; never establish origin from surname, appearance or language alone.
2. Load only the matching profile from the [country starter database](assets/countries/index.json), using scripts/country_tools.py if available. Read [country-database.md](references/country-database.md). If no profile exists, continue the same open discovery protocol; do not select a country from a surname. For each relevant country and period, identify what records this person’s events and activities could have generated. Consider civil/religious, household, legal/property, migration, occupational, institutional, press and private sources as relevant.
3. Discover local source terminology in the country’s languages. Search official research guides and catalogues, then scholarly or community finding aids. Use secondary guides as discovery leads and verify collection coverage with custodians.
4. Investigate both sides of migration. Destination marriage, death, residence or naturalisation records may identify an origin locality; departure and origin-family records may test identity. Include transit and former administrative powers when evidence makes them relevant.
5. Pass country, period, locality, creators and desired information to repository-discovery. Do not equate country coverage with one national archive or one commercial website.
6. Build a person-specific source portfolio. Present the three most useful leads with reasons and a next action, retaining the complete portfolio internally. For each collection state the question it could answer, expected information, coverage, custodian, access route, supporting URLs, status and priority rationale.
7. Reuse country profiles as dated starting knowledge, not a closed list. Refresh when an endpoint fails, a new jurisdiction appears, source survival is unclear or guidance is stale.
8. Trigger a new discovery branch when a source changes an origin. Preserve prior branches and why they were rejected or paused. Report countries/periods still uncovered and an actionable next step.

## Output contract

Per-person source portfolio; country profiles with evidence and verification dates; cross-border search links; hypotheses and uncovered branches.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not claim a source exists just because that record type is common elsewhere. Distinguish confirmed holdings, plausible leads and inaccessible/unknown coverage. Prioritize information gain over famous websites.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Search/fetch in relevant languages; repository registry; historical locality profiles; collection catalogues.

## Handoffs

Repository-discovery verifies custodians and access; planner orders the portfolio; locality-research resolves ambiguous origin names.

## Example

An arrival document names a previously unknown village. Reopen locality discovery for that village, find its period jurisdiction, then rebuild the origin-country source plan.

## Bundled resources

- [country-discovery.md](references/country-discovery.md)
- [record-families.md](references/record-families.md)
- [country-profile-template.json](assets/country-profile-template.json)

- [country-database.md](references/country-database.md)
- [country index](assets/countries/index.json)
- [country schema](assets/country.schema.json)
- [country_tools.py](scripts/country_tools.py)
