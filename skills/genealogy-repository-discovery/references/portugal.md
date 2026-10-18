# Portugal discovery seed

Guide pages checked during design on 2026-10-16. Authentication, individual record access and API support were not tested. Reverify a target collection and current service instructions at use time. This seed is intentionally incomplete and must be expanded for the person's actual places, dates and activities.

## Distinguish institutions and services

| Entity and official route | Discovery role |
| --- | --- |
| [DGLAB archives](https://arquivos.dglab.gov.pt/) | Starting hub for archival networks, directories, finding aids and services. Follow links rather than guessing addresses. |
| [DGLAB regional archive directory](https://arquivos.dglab.gov.pt/rede-portuguesa-de-arquivos/rede-dgarq/arquivos-regionais/) | District/regional discovery, with university-administered and autonomous-region exceptions. Verify linked institutions and holdings. |
| [Torre do Tombo](https://antt.dglab.gov.pt/) and [research guide](https://antt.dglab.gov.pt/pesquisar-na-torre-do-tombo/) | Custodian/research guidance. Its site describes shared cataloguing with the former Lisbon district archive. |
| [Digitarq](https://digitarq.arquivos.pt/) and [help](https://digitarq.arquivos.pt/help) | Multi-repository catalogue, digital access and service routes. Determine the actual custodian on each description. |
| [CRAV](https://crav.arquivos.pt/) and [DGLAB explanation](https://arquivos.dglab.gov.pt/programas-e-projectos/modernizacao-administrativa/crav/) | Request/service channel. Current Digitarq also presents request services; recheck integration and login routes. |
| [IRN](https://irn.justica.gov.pt/) and [online services](https://irn.justica.gov.pt/online) | Registration authority and certificate-service routes. Discover the relevant office and actual record availability. |
| [IRN contact directory](https://irn.justica.gov.pt/Contactos/Lista) | Verify current office/contact route; no guessed email patterns. |
| [Arquivo da Universidade de Coimbra](https://www.uc.pt/auc/) | Follow the DGLAB directory's university-archive exception; verify collection coverage at the institution. |
| [Arquivo Distrital de Braga institutional page](https://www.uminho.pt/PT/uminho/Orgaos-da-Universidade/Unidades-Culturais/Paginas/Arquivo-Distrital-Braga.aspx) | University of Minho archive with regional functions; use institution-linked catalogue access. |
| [Arquivo Histórico Ultramarino](https://ahu.dglab.gov.pt/) | Candidate branch when evidence concerns overseas administration; investigate actual holdings and corresponding destination-country sources. |

## Example discovery routes

- Old parish event: identify historical parish/municipality/diocese -> relevant district/regional or other verified custodian -> parish fonds/series/volume -> actual dates/gaps/images -> request or onsite route if needed.
- Civil registration: identify event and period -> IRN/conservatória and archival guides -> verify whether the required register is retained or transferred -> appropriate certified-copy or research route.
- Property/building question: investigate municipal, property-registration and notarial/judicial creators separately. Search by property, owner, reference and transaction period as relevant. Do not assume a municipal building file is in a national catalogue.
- Military question: establish service branch, period and plausible record creator; discover that service's archives through official institutional pages. A national archive search alone is not coverage of all military sources.
- Overseas or migration question: investigate origin, destination and relevant administrative creators; records may be distributed across countries.

## Native-language discovery queries

Use context-specific variants of: `Portugal arquivos genealogia`; `[localidade] arquivo municipal fundos`; `[distrito] registos paroquiais`; `[instituição] arquivo histórico`; `[freguesia] baptismos [intervalo]`; `[conservatória] transferência livros arquivo`; `[instituição] serviços reprodução certidão pesquisa`.

Search spellings such as batismo/baptismo and historical place forms without silently changing source wording. Distinguish record date, description date and access date.

## Important limitations

Do not encode a blanket age threshold as proof of custody. General guidance can route a search; collection holdings determine actual availability. Do not treat every Portuguese archive as part of the same platform or administrative network. University, municipal, church, regional and private repositories require discovery.

Do not treat CRAV, Digitarq and Torre do Tombo as independent evidence for the same record. Preserve source identity and access-channel relationships. This package asserts no public API for these services. A host project may document endpoints that the official viewer itself calls (search, digital object, file delivery); use them only under step 6 of the skill: documented by the host project with provenance, a check date and scope, and recorded in `route_provenance`. Do not derive further endpoints or identifiers from them.
