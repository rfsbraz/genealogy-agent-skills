---
name: genealogy-repository-discovery
description: "Discover and verify archives, registries, libraries, collections and access services for a place, period and question. Use for new jurisdictions, unavailable records, custody transfers or stale repository profiles."
disable-model-invocation: true
---

# Discover Archives and Custodians

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task.

## Inputs

Research context; candidate record creators; country/region/period; expected record type; known references; existing repository registry.

## Procedure

1. Load references/discovery-protocol.md. For Portugal also load references/portugal.md; treat this seed as an example, not a restriction on countries or institutions.
2. Search native-language concepts for national archives, archival networks, civil registration and relevant institutional record types. Follow authoritative directories, municipal/university/church sites and collection guides. Do not restrict trust to one domain suffix.
3. Classify every discovered entity: record creator, custodian, directory/aggregator, catalogue/viewer, request service or commercial intermediary. Link these roles explicitly. A catalogue and a repository may expose the same source.
4. Expand by historical geography and institutional responsibility. Check relevant local, district/regional, national, religious, university, military, judicial, private and overseas repositories; document which categories matter and why.
5. Follow custody: read collection histories, transfers, successor institutions and deposits. Use general transfer rules only as leads. Verify the actual collection, locality, dates, gaps and reference code with a holding description or an attributed custodian reply.
6. Inspect access separately: description online, name index, browsable images, request, onsite, restricted, unknown. Discover catalogue and request URLs from institutional links; never invent API endpoints or manipulate IDs as a substitute for discovery. An endpoint documented by the host project counts as a discovered route when the document gives its provenance (for example observed from the official viewer), the date it was checked and its scope. Record the documenting file, provenance and check date in the profile's `route_provenance`, and say which route each search used. An undocumented or unchecked endpoint stays a guess.
7. Record official supporting pages, aliases, repository roles, coverage evidence, contact routes, access status and verification dates. Retain superseded endpoints with redirects/history, not as independent repositories.
8. If a site fails, record the failure and seek a current official route or prepare an enquiry. A technical failure is not a negative record search. Stop after relevant categories and plausible custody routes are checked, or mark bounded discovery incomplete.

## Output contract

Verified repository profiles; collection coverage entries; creator-custodian-platform-service links; ranked access routes; unresolved custody questions.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Never equate no indexed result with no holding. Never infer all records are digitised from an online catalogue. Keep candidates separate from verified relevant holdings and preserve discrepancies between official pages.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Web search/fetch; catalogue browsing; repository registry; optional documented IIIF/OAI-PMH tools. Protocol support must be verified per repository.

## Handoffs

Acquisition uses the selected collection and endpoint; correspondence handles enquiries; locality research handles jurisdiction ambiguity.

## Example

For Portugal, discover DGLAB links, distinguish Torre do Tombo from Digitarq and CRAV, locate relevant district or university custodians, and verify the particular collection’s access route.

## Bundled resources

- [discovery-protocol.md](references/discovery-protocol.md)
- [portugal.md](references/portugal.md)
- [repository-profile-template.json](assets/repository-profile-template.json)

## Country starter handoff

Use origin-source-discovery’s country profile to identify promising official directories and services. Verify the actual custodian, collection, locality and dates. Preserve the distinction between repository, catalogue and request service (for example, Torre do Tombo, Digitarq and CRAV). New local archives discovered from the question become sourced portfolio entries; the national seed list never bounds discovery.
