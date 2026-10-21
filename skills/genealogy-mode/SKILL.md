---
name: genealogy-mode
description: "Use when the user wants to start a genealogy case, research ancestors or descendants, or resume family-history work; plans and routes to specialists. Not for code trees or DNA kit shopping."
license: MIT
compatibility: "Python 3.10+ for the local case helpers (standard library only)."
metadata:
  author: Rodrigo Braz
---

# Research Your Family History

Read the [shared research contract](references/shared-contract.md) and [data model](references/data-model.md) before writing case state. Resolve sibling skills by their declared names if the host uses different folder names. This suite assumes the coordinator is installed alongside its workflow skills. Read only additional references relevant to this task.

## Simple entry point

Use [easy-use.md](references/easy-use.md) for every user-facing interaction. Accept “start my tree / interview me”, “research this person”, “read this document”, “tell their story”, or “show progress / continue”. Route conversational tree setup to genealogy-interview and literary/novelized biography to genealogy-narrative. Normal language is enough; optional chat shortcuts are defined in references/chat-commands.md. Choose specialist skills internally and begin from what the user already supplied. Present one useful next action; do not expose a specialist-skill menu or require a new intake questionnaire.

## Loading specialists

Specialist skills are user- or mode-invoked: on hosts that support it they do not load on their own, and only genealogy-mode, genealogy-interview and genealogy-narrative trigger automatically. When this procedure routes to a specialist, read that skill's `SKILL.md` from its sibling folder (resolved by declared name) and follow it, loading its references as it directs. The user can still call any specialist directly.

## Inputs

User goal; existing case or supplied material; authorized scope, time and spending limits; host capabilities; prior decisions and outstanding requests.

## Procedure

1. Load references/shared-contract.md, references/data-model.md and references/tool-contracts.md. Discover actual host tools. Treat names in the tool contract as interfaces to map, not callable tools that necessarily exist.
2. Open the current case. If none exists, route an interview request to genealogy-interview; otherwise call genealogy-case-intake. Interview readiness does not imply genealogical proof. A story request reads the case through genealogy-narrative and does not mutate evidence. Read authoritative project files before chat summaries. Set a single active question and a queue of others; distinguish ancestry expansion, identity resolution and life-history research.
3. Record which actions are authorized. Research authorization does not itself authorize email sending, purchases or public tree changes. Reuse explicit standing authorization within scope; do not ask repeatedly for already authorized actions.
4. Route through locality, origin-source and repository discovery when geography, period or source needs are new or stale. For every newly identified origin, repeat discovery for the affected person; do not limit the investigation to a country whitelist.
5. Ask the planner for the next action and why it can distinguish hypotheses. Acquire and read a small useful batch, then reassess. Do not postpone analysis until an entire website has been searched.
6. For long documents or an explicit quick-reading request, route to genealogy-transcribe-quick and register page coverage with genealogy-document-processing. Escalate selected pages to genealogy-transcribe-detailed, which uses genealogy-read-manuscripts for handwriting. Keep extraction, quick and detailed coverage distinct. Route semantic translation to historical-translation, extraction before identity resolution, and collateral research to family-reconstruction. Keep incidental leads in the queue.
7. Evaluate any proposed conclusion using genealogy-proof-evaluation and the [GPS policy](references/gps-policy.md). Use `source_supported` for a cited, scoped finding assessed against the currently consulted evidence, without representing it as full proof. Keep unassessed or materially disputed leads provisional/unresolved. Require a current five-element review before `supported` or definitively `rejected`. For consequential disputed relationships, request independent review if fresh agents are available and within budget. A second opinion is analysis, not another historical source.
8. If evidence is inadequate, return to planning when a meaningful next action exists. Otherwise record blocked, unresolved or paused with a specific restart condition. Time exhaustion is not proof of exhaustive research.
9. Checkpoint after each acquisition batch, important interpretation and external action. Store the question, current hypotheses, searches completed, pending requests, source IDs and exact next step. Resume from this state without replaying completed external actions.
10. Finish with reporting and maintenance using the brief progress card in easy-use.md unless the user requests detail. Record supported, provisional and rejected conclusions separately, the work actually performed, limitations, cost when measured, and next questions. Ask only for missing information that materially blocks further useful work.

## Output contract

Case checkpoint; selected skills; question and hypothesis queue; bounded action plan; cited progress or final report; blocked-action list with restart conditions.

Use the shared handoff envelope: case/question IDs, status, artifacts and evidence IDs, findings, uncertainties, actions actually performed, next actions and blockers. Store observations before conclusions; preserve field-level uncertainty.

## Quality gates and failure handling

Never claim a tool, archive visit, email or independent review ran without a result. Do not silently broaden spending or communication scope. Stop a repetitive search loop when no new information or justified variation is being introduced. Reopen dependent conclusions after a correction.

If a required capability is unavailable, record what was and was not done, use a documented available fallback, and return a specific handoff. Never simulate a successful external action or fabricate a source, citation, tool result or reviewer report.

## Tools and dependencies

Case read/write, web search, document access, task ledger, optional specialist agents. Use scripts/case_tools.py for a portable JSON case skeleton and structural validation; it is not a database server.

## Handoffs

Intake -> setting and discovery -> planning -> acquisition -> extraction -> identities and families -> proof/review -> maintenance/reporting. See references/skill-routing.md for entry points.

## Example

“Identify this person’s parents.” Start from the document, distinguish its statements from accepted parentage, discover relevant jurisdictions, and finish with proof or an explicit unresolved question.

## Bundled resources

- [Chat commands and modes](references/chat-commands.md)
- [easy-use.md](references/easy-use.md)
- [gps-policy.md](references/gps-policy.md)
- [gps-review-template.json](assets/gps-review-template.json)
- [gps-review.schema.json](assets/gps-review.schema.json)
- [data-model.md](references/data-model.md)
- [host-adapter.md](references/host-adapter.md)
- [host-adapter-contract.json](assets/host-adapter-contract.json)
- [host_adapter.py](scripts/host_adapter.py)
- [shared-contract.md](references/shared-contract.md)
- [skill-routing.md](references/skill-routing.md)
- [sources.md](references/sources.md)
- [tool-contracts.md](references/tool-contracts.md)
- [case_tools.py](scripts/case_tools.py)
- [case-template.json](assets/case-template.json)
- [case.schema.json](assets/case.schema.json)

## Corrections and generated repository views

For “reread/correct this passage”, route the original through detailed reading, freeze the result, then use scripts/research_updates.py `reread`. For “update facts/tree notes”, use its `project` command. Read [revisions-and-projections.md](references/revisions-and-projections.md) before these operations. In case-canonical mode, edit evidence once in the case; fact files and tree notes are generated outputs. In a repository that remains canonical, derive a temporary case view and apply corrections only through that repository's reviewed adapter, which follows the [host adapter contract](references/host-adapter.md). Never establish two editable authorities or silently migrate a live repository.
