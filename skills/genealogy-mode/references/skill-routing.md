# Routing and invocation

Invoke the coordinator for an end-to-end investigation. A user may also enter directly at any specialist; preserve the same evidence contract.

| Situation | Route |
| --- | --- |
| Conversational tree setup, interview, resume or correction | genealogy-interview |
| New project audit or imported tree | genealogy-case-intake |
| Evocative / novelized life story | genealogy-narrative |
| Ambiguous or historical place | genealogy-locality-research |
| New origin, residence, migration or country | genealogy-origin-source-discovery |
| Unknown custodian/catalogue/service | genealogy-repository-discovery |
| Need the next discriminating action or stuck search | genealogy-research-planner |
| Known context; locate collections/entries | genealogy-source-discovery |
| Fetch/browse/preserve records | genealogy-record-acquisition |
| Quick pass over a long document | genealogy-transcribe-quick |
| Detailed page/region reading | genealogy-transcribe-detailed; genealogy-read-manuscripts for handwriting |
| Processing coverage, token budget and reread backlog | genealogy-document-processing |
| Language/terminology/calendar interpretation | genealogy-historical-translation |
| Convert a source into attributed observations | genealogy-evidence-extraction |
| Namesakes/aliases/proposed merge | genealogy-identity-resolution |
| Household/kinship/associate network | genealogy-family-reconstruction |
| Accept or reopen a claim | genealogy-proof-evaluation |
| Challenge consequential reasoning | genealogy-independent-review |
| Contact record holder or handle a reply | genealogy-archive-correspondence |
| Interview or family collection | genealogy-oral-history |
| Onsite/human record-agent work | genealogy-archive-fieldwork |
| Consented DNA evidence | genealogy-genetic-evidence |
| Save/correct/synchronize research | genealogy-research-maintenance |
| Report/biography/tree/handoff | genealogy-reporting |
| Measure system or skill behaviour | maintainers only, see evaluation/ |

Suggested loop: intake -> setting/origins/repositories -> plan -> discover/acquire -> read/extract -> identity/family -> proof/review -> maintain/report. Loop back when evidence changes the question. Preserve an unresolved exit when research cannot currently decide.

## Invocation

Only genealogy-mode, genealogy-interview and genealogy-narrative load on their own. Every other skill is user- or mode-invoked: it sets `disable-model-invocation: true` for Claude Code and Cursor and `policy.allow_implicit_invocation: false` in `agents/openai.yaml` for Codex. To route to one, read its `SKILL.md` and follow it. Gemini CLI cannot enforce this and may still load a specialist on its own.

## Installation dependency

Install the suite together. New workflow skills depend on genealogy-mode's shared references. Resolve cross-skill references by declared name when a host renames installation directories. `genealogy-read-manuscripts` is bundled with the current four-method protocol and remains usable on its own; do not create a duplicate with the same declared name in a host that already has it.

genealogy-read-manuscripts uses four distinct methods in separate contexts; the same model is valid. Fresh calls may run sequentially. If the host cannot isolate contexts, retain the four-method plan, disclose the shared context, and never simulate completed fresh calls. Tool availability and instructions from the host/user always govern execution.
