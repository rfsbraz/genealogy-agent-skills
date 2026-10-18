---
name: genealogy-genetic-evidence
description: "Integrate consented DNA evidence with documentary genealogy for ancestry and kinship questions. Use only when DNA data is supplied or explicitly authorized and a genetic hypothesis is relevant."
disable-model-invocation: true
---

# Assess Genetic Genealogy Evidence

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task.

## Inputs

Research question; test type and provider; consent/use scope; match and segment information actually available; documentary pedigrees; known uncertainty.

## Procedure

1. Verify who controls the data, the authorized uses and sharing limits. Do not upload raw DNA or match lists to new services or contact matches without explicit authority. Record unexpected-relationship handling preferences where relevant.
2. Identify autosomal, Y-DNA or mitochondrial evidence and what it can address. Preserve provider, test date, metrics and provenance; do not treat ethnicity estimates as proof of nationality or a named ancestor.
3. Build documentary relationship hypotheses first, including alternatives. Distinguish a genetic relationship hypothesis from an identity assignment to a particular historical person.
4. Examine relevant shared DNA, segment information, inheritance paths and match networks where available. Use current specialist references/tools and their assumptions; record tool versions and actual inputs/outputs.
5. Consider endogamy, pedigree collapse, multiple relationships, sample/test limits and incomplete trees. Shared matches are not automatically triangulated segments. Absence of an autosomal match does not universally exclude a genealogical relationship.
6. Compare genetic patterns with documentary timelines, places and family evidence. Do not turn a single shared-DNA amount into one exact relationship without alternatives.
7. Report what is supported, unresolved and outside competence. Recommend a specialist or additional consented evidence when the available analysis cannot distinguish candidates.

## Output contract

Consented evidence inventory; documented hypotheses; genetic/documentary comparison; limitations and next evidence.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not make medical diagnoses or sensitive identity assertions beyond the supplied evidence. Do not claim calibration or genetic expertise that the host lacks. Keep identifying DNA data out of public reports by default unless explicitly authorized.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Authorized DNA exports and documented analysis tools only; no DNA vendor connector is bundled. Use documentary workflows when genetic tools are unavailable.

## Handoffs

Proof-evaluation integrates conclusions; correspondence manages authorized match contact; reporting enforces disclosure scope.

## Example

A DNA amount fits several cousin relationships. Retain alternatives and use documentary generations and additional matches to discriminate.
