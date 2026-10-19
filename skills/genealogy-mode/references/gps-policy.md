# Genealogical Proof Standard in this suite

Primary basis: [Board for Certification of Genealogists, Ethics and Standards](https://www.bcgcertification.org/ethics-standards), GPS section, checked 17 October 2026. This is our operational implementation of the five elements, not BCG endorsement or certification. The checker validates records and references; a competent reviewer must judge the evidence and reasoning.

## Five required assessments

| Element, in plain language | Owner | Required research work |
|---|---|---|
| Look broadly enough for this question | research-planner + source discovery + proof-evaluation | Justify the relevant record families, locality/period coverage, alternatives, searches performed and remaining gaps. |
| Make each source traceable | acquisition + extraction + proof-evaluation | Cite the version actually consulted, its origin/custodian, identifying details and exact passage. Check the citation against that material. |
| Compare and interpret the evidence | extraction + identity-resolution + proof-evaluation | Correlate dates, people and context; assess source form, informants, information quality, relevance and dependence. |
| Explain contradictions | proof-evaluation + independent-review when available | Include counterevidence and explain each material discrepancy. Do not settle conflicts by vote or convenience. |
| State a reasoned answer | proof-evaluation + reporting | Write the claim, evidence chain, reasoning, limitations and what would reopen it. Scale statement/summary/argument to the problem. |

The five assessments are cumulative. There is no points total or percentage-confidence shortcut, and no requirement to transcribe every page of every discovered volume. A source count alone cannot establish proof. BCG’s published guidance on simple proof statements calls for at least two supporting citations across the statement and its broader documented context; individual facts may have one immediate citation within that context. Do not require two documents mechanically for every field, or treat a lone isolated record as automatically sufficient. See [Proof Statements 1](https://bcgcertification.org/ten-minute-methodology-proof-statements-1) and [Examples](https://bcgcertification.org/ten-minute-methodology-proof-statements-2-examples), checked 17 October 2026. The validator does not count citations to certify adequacy; the reviewer must assess the contextual support. Relevant unread or illegible passages can still be material gaps. A budget pause, access failure or completed source shortlist does not establish adequate research.

## Claim lifecycle

1. Record observations and citations, including uncertain readings, before deciding identity or parentage.
2. Record useful scoped findings as `source_supported` under the v1.4 rules below; maintain unassessed working leads as `provisional` or questions as `unresolved`. These may be saved and reported without a full review.
3. Before accepting `supported`, or definitively `rejected`, complete a `gps_review` on that conclusion using `assets/gps-review-template.json`. These are claim-level decisions. Keep weaker candidate rejection as provisional/unresolved with its current reason.
4. Assess every recorded hypothesis for the question, its supporting evidence and counterevidence. Explain unrecorded alternatives considered in the analysis narrative. Absence becomes negative evidence only with an expectation of occurrence, survival/coverage and an adequate search; document that basis.
5. For every reviewed observation, provide a citation with `text` and `locator`, an information-quality/relevance assessment and a source/informant/independence assessment. Unknown informants are acceptable when explicitly analysed; never invent details to complete a field.
6. Record coverage dispositions and explain gaps. `material` means an unresolved issue that could affect this conclusion. An unavailable source may still prevent support. If judged nonmaterial, explain why and what substitutes were used. No unaddressed material gap or conflict may accompany `ready`.
7. Set the intended conclusion and relationship states, then compute `case_tools.py evidence-digest CASE.json`; put that digest in every review of this evidence snapshot. Enter the real reviewer and date; set `decision: ready` only after substantive assessment.
8. Run `case_tools.py validate CASE.json --gps` before accepting/exporting the view. Repair missing work or retain a working/unresolved status; do not weaken the gate to make a check pass.
9. Reassess after changes to evidence, identities, questions or conclusions. The digest conservatively covers the case evidence graph; checkpoint/task/mail bookkeeping alone does not invalidate it. Preserve old reviews in change history before replacing them.

The validator checks all five assessment statuses, cited references, source/information assessments, recorded alternatives, material gaps/conflicts, dependency status and the evidence fingerprint. It cannot discover unrecorded counterevidence, verify an informant's honesty, decide whether an argument is persuasive, or authenticate reviewer identity. Host writers/exporters must invoke it; editing a JSON file directly is not a security boundary.

## Versions and adoption

New v1.4 cases use case schema `1.2`: the GPS review requirement is enabled by the version and cannot be disabled by a boolean preference. Existing `1.0` cases remain structurally readable; `--gps` reports their review gaps without rewriting them. All full-proof claim acceptance and public projections must use the strict check even when the imported case is old. Private generated research views may include clearly labelled source-supported or provisional findings.

Do not upgrade old `supported` statuses into a claim that GPS was met. Keep the original state as an attributed legacy assessment, review one claim at a time, and only then migrate it into the reviewed view. A validator pass is documented review completeness, not historical truth.

## Source and information distinctions

Keep `source_type` (image, index, testimony etc.) separate from assessed source form (original, derivative, authored or undetermined). A faithful image can represent an original record. Information can be primary, secondary or undetermined for a particular statement. Evidence can answer the question directly, indirectly or through a justified absence. None of these labels is a universal truth ranking. An original can contain erroneous information, and multiple copies do not become independent sources.

## v1.4: useful findings before full proof review

Case schema 1.2 adds `source_supported`. This means a specific finding has been assessed against cited, consulted evidence; its scope and limitations are recorded, and no known unresolved material conflict is hidden. It does not claim reasonably exhaustive research or completion of the full GPS. It can appear in research reports and a working tree with its label, without waiting for every question to be closed.

When the working tree is also the published tree, that label alone is not enough. A `source_supported` conclusion may enter that tree only if the host's publish build provably excludes or visibly labels non-`supported` conclusions, and the host adapter declares which. If the build cannot do that, keep `source_supported` conclusions out of the tree (as proposals or in a private sidecar) until they reach `supported`. A `source_supported` relationship must not create an ancestry edge in that tree; shared-contract.md treats it as usable with qualification, not as an accepted proof-reviewed ancestry edge.

Store a compact `evidence_assessment`: basis, scope, reviewer, reviewed_on, known_conflicts (description, material, resolved, reason), and limitations. Include full citations for every supporting observation and assess dependencies. Mere legibility, a name match or an agent vote is insufficient. Use a narrow claim such as “the marriage entry identifies João as her father” when all that is established is the record statement. Keep an untested cross-record identity or contradicted parentage provisional/unresolved. Report the stated age as an age, not an invented exact birthday.

Use `supported` and `rejected` for decisions with a current full review, as before. Do not automatically promote old provisional conclusions. `source_supported` needs a real assessment and schema 1.2; it is not a renamed provisional status. Rereading a supporting observation invalidates its claim assessment and affected dependencies. Schema 1.0/1.1 remain readable; full-review requirements are unchanged. The offline validator checks completeness and references, not whether the reviewer has reasoned correctly.
