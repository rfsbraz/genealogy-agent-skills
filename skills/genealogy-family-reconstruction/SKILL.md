---
name: genealogy-family-reconstruction
description: "Use when genealogy-mode or the user needs households, kinship or community networks rebuilt from linked evidence. Not for deciding if two mentions are one person."
license: MIT
metadata:
  author: Rodrigo Braz
disable-model-invocation: true
---

# Reconstruct Families and Networks

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Resolved and candidate identities; observations; household/event timelines; locality context; research question.

## Procedure

1. Build event-based households and relationships with dates and roles. Separate biological, adoptive, step, guardianship, social and unspecified relationships; retain the source’s terminology.
2. Reconstruct spouses, children and siblings using independent evidence across life events. Do not infer missing parents or children to make a tree symmetrical.
3. Track relatives and associates as a network: witnesses, godparents, neighbours, employers, co-travellers and executors. Store association type and source; repeated association alone does not establish kinship.
4. Correlate addresses, property, naming, inheritance and migration across the network. Generate explicit relationship hypotheses and alternatives, not accepted edges.
5. Look for reused names after child deaths, multiple marriages, changes of household, adoption and guardianship where evidence suggests them. Do not assume all children of a spouse are biological children of the other spouse.
6. Check graph consistency: self-parent edges, ancestry cycles, duplicate candidate mappings and time conflicts. Pedigree collapse is legitimate; do not confuse repeated ancestors with a directed ancestry cycle.
7. Explain each proposed relationship with supporting and opposing evidence. Keep unclear families in candidate groups until identity/proof review resolves them.
8. Queue collateral searches only when they help the active question or the user’s explicit broader family goal.

## Output contract

Dated household and kinship graph; association network; relationship hypotheses; unresolved links; evidence-based follow-up questions.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not equate godparent, witness, neighbour, surname or household member with a blood relative. Distinguish reconstruction completeness from research success.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Case graph/query; timeline checks; source-linked diagrams; family group templates.

## Handoffs

Identity-resolution separates namesakes; proof-evaluation assesses relationships; reporting builds trees with uncertainty visible.

## Example

A witness repeatedly appears at baptisms. Store the witnessed events and investigate the association without declaring an uncle relationship.
