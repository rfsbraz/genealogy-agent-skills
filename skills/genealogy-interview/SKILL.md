---
name: genealogy-interview
description: "Use when the user says 'start my tree', 'interview me' or /tree: builds a first family tree one question at a time. Not for searching records, which genealogy-mode handles."
license: MIT
compatibility: "Python 3.10+ for the interview helper (standard library only)."
metadata:
  author: Rodrigo Braz
---

# Start a Tree by Talking

Read the coordinator's [shared contract](../genealogy-mode/references/shared-contract.md) and [data model](../genealogy-mode/references/data-model.md). Use [interview-protocol.md](references/interview-protocol.md) for question selection and handoff. Read [storage.md](references/storage.md) before using the local helper.

## Begin immediately

Reuse the goal, people and documents already supplied. Do not make the user fill in a form or repeat known details. If nothing is supplied, ask: “Who would you like to start with: yourself or a relative?” Ask one short question per turn. A nickname, relationship or unnamed person is enough; exact dates and documents are optional.

Follow the user's language. Accept short answers, a long family story, “I don't know”, “skip”, corrections and changes of subject. Interpret plain language and optional chat shortcuts identically. Shortcuts are a host-independent convention, not installed slash commands.

## Conversation loop

1. Load the current case and interview checkpoint. For an existing tree, reuse its IDs and ask about gaps. Do not overwrite it or merge identities by spelling. New helper cases remain separate seeds until deliberately merged through maintenance.
2. Capture the answer verbatim with speaker, actual date, question and stable turn ID. Extract every useful supplied detail. Separate direct memory, family hearsay, inference and unspecified knowledge; leave the basis unspecified until it matters enough to ask.
3. Create provisional person candidates, source mentions, cited observations and provisional relationship conclusions. Preserve uncertainty in dates, places and names. Display “reported by you” rather than “verified”. Never ask the user to certify GPS compliance.
4. Preserve partial dates, candidate localities and unspecified relationship kinds. Separate biological, adoptive, foster, step and guardian roles. Accept any family structure and multiple partners. Do not require sex, civil status or genetic details.
5. Give a short acknowledgement, then ask the highest-value next question: target; link to a known relative; rough time/place; basis for a key detail; promising document. Skip answered or declined questions. Avoid leading questions and surname-based country assumptions.
6. After roughly 3–5 useful answers, or on request, show a small starting tree/list and uncertainties. Do not demand a complete pedigree. On “research now”, start from what is available; if no search can be scoped, ask the single question that would unlock it.
7. On correction, append a new turn and observation. Supersede only the affected provisional assertion, retain its original wording/citation and record the reason. Route identity conflicts and reviewed claims through maintenance and proof evaluation.
8. On pause, save the exact pending question and next action. On resume, give one sentence of context and continue. Never restart the whole questionnaire.

## Finish with something useful

Provide a compact tree with provisional links visible, what the user reported, missing/contradictory details, one active research question, and up to three ranked next actions. Save supporting interview citations. A document mentioned by the user remains a lead until inspected. Route to case-intake, locality/origin discovery and research-planner. Use oral-history for deeper interviews or another relative's testimony; contact requires applicable authorization.

Default a new case to private. Participating in this requested interview authorizes saving supplied answers in the case; do not add repeated consent prompts. Sharing, recording another person, mail and payments retain separate authority. Keep family data out of reusable skill files and public fixtures.

## Tools and limits

The [local helper](scripts/interview_tools.py) creates a seed case, validates/applies an agent-prepared turn, and shows a resume summary. It does not parse natural language, run a chat, merge an existing tree or conduct research. The host agent handles those steps. If storage is unavailable, provide a handoff and state that it was not saved.

The helper uses atomic replacement, an expected-revision check and a lock. Repeated identical turn IDs are idempotent. Never remove an active lock or force a stale revision; reload and reconcile. Evidence changes to cases with supported/rejected conclusions require maintenance.

## Resources

- [Interview protocol](references/interview-protocol.md)
- [Storage and commands](references/storage.md)
- [Turn schema](assets/turn.schema.json)
- [Example turn](assets/turn.example.json)
