---
name: genealogy-locality-research
description: "Use when genealogy-mode or the user needs a historical place resolved to its jurisdictions, institutions and record practices. Not for finding the records held there."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Historical Locality Research

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Literal place strings and source locators; event period; possible country or region; record type; evidence of denomination or institutional affiliation.

## Procedure

1. Preserve literal place spellings and languages. Enumerate candidate places when the name is ambiguous; retain the unresolved candidates instead of choosing the most famous locality.
2. Consult period maps, gazetteers, official histories and archival authority records. Distinguish parish, municipality, district, diocese, state and country. Record historical names and date-bounded jurisdiction changes.
3. Identify the institutions likely to create the desired records in that time and place. Establish when each record practice existed and whether coverage includes the relevant population.
4. Investigate naming, language, calendar and registration conventions needed to interpret the actual documents. Use sourced local rules; do not assume universal surname inheritance, marriage naming or date order.
5. Separate historical jurisdiction from modern repository location. Map successor institutions and plausible custody transfers as leads requiring verification.
6. Produce a locality profile containing alternatives, sources and last-checked dates. Normalize dates or coordinates only when justified; record precision and preserve the original strings.
7. Flag assumptions that change the next search. Ask for a sharper locality only if available evidence and useful broad discovery cannot resolve it.

## Output contract

Place candidates; historical jurisdiction timeline; record-creator map; naming/calendar notes; cited locality profile and remaining uncertainty.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Modern administrative borders do not automatically apply to old events. A birthplace or nationality inferred from a surname remains a hypothesis. Absence from a modern map is not evidence that a locality never existed.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Web search/fetch; maps/gazetteers; official archive guides; date and place utilities if available.

## Handoffs

Send country and migration context to origin-source-discovery; creator/jurisdiction candidates to repository-discovery; language questions to historical-translation.

## Example

A marriage says “Santa Maria” without municipality. Keep candidate parishes and use residence, witnesses and nearby events to narrow them before choosing a repository.
