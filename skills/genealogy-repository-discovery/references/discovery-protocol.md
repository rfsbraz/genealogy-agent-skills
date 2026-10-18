# Repository discovery and verification

## Procedure

Use three linked investigations: creator -> current custodian -> access service. Search across geography and institutions; record why each lead matters. Begin with national archival authorities and directories where useful, then follow local, university, religious, military, municipal, judicial, private and cross-border branches relevant to the question.

Use official institution pages and holding descriptions to verify custody. A directory is a lead and can be outdated. Check the destination site's current identity, collection scope and access. Do not require a .gov domain: universities, churches and municipal institutions use varied domains. Prefer institution-linked contact details over search snippets.

Read fonds/series/volume descriptions and finding-aid PDFs. Trace former names and successor organisations, transfers, deposits and distributed holdings. Repositories can share custody or hold copies. Preserve physical custodian, digital host and certified-copy service separately.

Use browsing when name indexes do not cover the material. Check date/place scope and gaps at collection/volume level. Avoid an online-only inventory of sources: onsite and request-only holdings remain relevant.

## Profile schema

Required: id, name, aliases, roles, official_homepage, jurisdiction, relevant_creators, catalogue_urls, request_urls, contact_verification, holdings, discovery_evidence, checked_at, status, limitations.

Each `route_provenance` entry: route (URL or endpoint pattern); found_via (`official_link` when reached from institutional pages, `host_project_document` when a host project documented it); documented_by (the host file, for host-documented routes); observed_from (for example the official viewer page that calls it); checked_on; scope (what the route returns and for which collections). A route without provenance and a check date is not a discovered route.

Each holding: id, repository_id, title, reference_code, creator, date_range, place_coverage, record_types, gaps, access_modes, verification_evidence, verified_at, status.

Roles: creator, custodian, aggregator, catalogue, image_host, request_service, intermediary. Use multiple roles when justified. Status: candidate, verified_identity, verified_relevant_holdings, outdated, inaccessible, rejected. Do not let a single scalar status hide collection-level gaps.

## Discovery trace

Record each useful step: query or originating page; discovered link; entity role; supporting statement; verification result; next route. Record failed endpoints without treating failure as proof of missing records. When a search returns a capped or truncated list (for example 40 of N hits, or only the first page), record the cap, the number shown and the total if stated, and mark that search's coverage partial, never complete. Record how the remaining items were reached, such as narrower queries or one reference code at a time, and which items stay unchecked. Keep contact channels verified and scoped to the department.

## Refresh policy

Refresh before externally consequential actions and whenever links fail, official pages conflict, the relevant period changes or the last verification is inadequate. No universal fixed TTL can guarantee accuracy. Keep last successful verification and latest failed attempt separately. Never overwrite a verified profile with unverified guesses.

## Completion check

- Is the creator/period jurisdiction understood sufficiently for this question?
- Have relevant repository categories and obvious exceptions been checked?
- Is at least one concrete holding or an attributed custody statement verified?
- Are dates, gaps and access modes known, or explicitly unknown?
- Is the next action reproducible from the profile?

If not, report bounded discovery incomplete with the exact unresolved custody/access question.
