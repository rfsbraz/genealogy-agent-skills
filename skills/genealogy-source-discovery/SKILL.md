---
name: genealogy-source-discovery
description: "Locate relevant collections, volumes, entries and source leads for an active genealogy question. Use after origin/repository mapping or when searching catalogues, indexes, published research and finding aids."
disable-model-invocation: true
---

# Discover Relevant Records

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task.

## Inputs

Question; source portfolio; repository profiles; period/place; name variants and known relatives; prior search coverage.

## Procedure

1. Review the source portfolio and catalogue scope. Learn whether the interface searches collection descriptions, indexed people, OCR or images; these produce different kinds of negative results.
2. Search in the source language using name variants, diacritics, historical spellings, institutional names and reference codes. Derive variants transparently; do not change the recorded name.
3. Browse hierarchy when name search is inadequate: repository, fonds, series, volume, entry. Use dates and geography to select volumes; record missing years and unindexed material.
4. Use published genealogies, indexes, local histories and community guides to identify underlying sources. Cite the guide actually seen; do not pretend to have consulted its cited originals.
5. Follow useful citation chains, related units, marginal references and linked creators. Compare reference codes to detect the same record exposed on multiple websites.
6. Capture candidate source ID, title, custodian, creator, dates, scope, endpoint, query/browse path, and why it may answer the question. Do not attach a candidate record to a person before identity assessment.
7. Log completed and incomplete coverage and technical failures distinctly. Return the most useful candidates and the next acquisition action.

## Output contract

Candidate collections/records with provenance, relevance and coverage; search log; request-ready references.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not invent a record, URL or reference number. Search snippets are leads, not substitutes for record inspection. Keep verified holdings distinct from plausible source types.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Web and archive search; catalogue hierarchy; documented metadata interfaces; source registry.

## Handoffs

Acquisition fetches records; repository-discovery resolves missing custodians; planner reprioritizes.

## Example

A parish catalogue lists a register but no person index. Return the volume and page-browsing route rather than a claim that the person was absent.
