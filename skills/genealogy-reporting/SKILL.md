---
name: genealogy-reporting
description: "Use when genealogy-mode or the user wants findings written up as cited reports, timelines, trees or handoffs. Not for literary life stories, which genealogy-narrative writes."
disable-model-invocation: true
---

# Report Family History

Read the [shared research contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md), [easy-use rules](../genealogy-mode/references/easy-use.md), [revisions and projections](../genealogy-mode/references/revisions-and-projections.md) and [host adapter contract](../genealogy-mode/references/host-adapter.md); read them when the task touches them.

## Inputs

Audience and format; active question; accepted/provisional conclusions; sources; search log; contextual research; sharing scope.

## Procedure

1. Follow the coordinator’s easy-use.md: default to a brief Finding / Why / Still uncertain / Next step card with citations, keeping the full audit available. A full-report request overrides this default. State the question and answer/status first. Include what was researched, which sources were actually used, material access limits and remaining uncertainty.
2. Build the report from current evidence-linked conclusions. Run strict GPS validation for accepted/rejected claims; distinguish legacy unreviewed conclusions. State agent versus human review accurately. Separate documented personal events, source assertions, researcher inference and general historical context. Keep factual biographies free of invented dialogue, motives or experiences. Route requested evocative or explicitly novelized narratives to genealogy-narrative, whose literary layer is labelled and remains outside evidence. This exception applies only to the story output, never to research conclusions.
3. Include precise citations and attributed quotations, respecting source-use restrictions and quoting only what is necessary. Refer to inaccessible originals through the source actually consulted.
4. Present relationships and timelines with uncertainty visible. Preserve literal names and dates where meaningful; explain modernized forms and calendar conversions.
5. Summarize conflicting evidence and why a conclusion was accepted or left open. Do not bury uncertainty in footnotes while drawing a certain tree edge.
6. Include a concise search/coverage summary and prioritized next actions. For handoff, provide source IDs, unresolved hypotheses, pending requests and the exact restart point.
7. Apply the audience’s disclosure scope to living-person and sensitive information. Internal case records and a public family narrative may need different content.
8. Use available document/PDF/diagram skills for requested formats and inspect rendered output. For GEDCOM, preserve a separate full research bundle and document export losses.

## Output contract

Cited report/biography/tree/timeline; source and search summary; limitations; next steps and handoff.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Do not present provisional relationships as established or general history as an individual’s lived experience. Do not represent a generated reconstruction as an authentic historic artifact.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Report renderer; documents/PDF; graph rendering; case export; citation formatter; storage.

## Handoffs

Maintenance saves outputs and revisions; orchestrator selects the next question; proof-evaluation resolves unsupported report claims.

## Example

Write a short biography distinguishing the person’s documented occupation from the broader economic history of the town.

## Bundled resources

- [research-report-template.md](assets/research-report-template.md)

## v1.4 finding labels

Report three useful distinctions plainly: the source states X; the assessed evidence supports X within the stated scope (`source_supported`); a current full review supports X (`supported`). Do not describe all unreviewed findings as mere guesses, or imply that source-supported means fully proved. Preserve known limits and conflicts close to the claim. Use generated private fact files/tree notes from the canonical case instead of manually copying findings into parallel editable files.
