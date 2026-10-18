# Interview storage

## Local helpers

From this skill directory:

```sh
python scripts/interview_tools.py new --out /private/family/case.json --language en
python scripts/interview_tools.py record /private/family/case.json --turn /private/family/turn-001.json --expected-revision 0
python scripts/interview_tools.py status /private/family/case.json
```

Use `assets/turn.example.json` as a synthetic example and `assets/turn.schema.json` as the contract. The host prepares the turn from the user's actual answer. Never substitute this example for a real interview or fabricate speaker/time metadata. The root package exposes equivalent `genealogy.py interview ...` commands.

The case keeps `schema_version: 1.1`. An optional `interview` property stores session metadata and append-only raw turns. Existing readers can ignore that property; no bulk migration is needed. Each turn becomes an attributed testimony source and full citation. Each assertion becomes an observation and provisional conclusion. Supplied new people get IDs and source mentions. Parent relationship direction is parent -> child; sibling/partner semantics are explicitly typed. Use unspecified parentage when biology is unknown.

`people` contains only new people. Assertions refer to existing or newly supplied IDs. Never recreate an existing ID to update a label. Label changes, identity linkage and mergers go through maintenance with history. `life_status: unknown` and private visibility are conservative defaults, not claims about whether someone is living.

`knowledge_basis` is firsthand, hearsay, inference or unspecified. All observations retain `evidence_class: testimony`; an interviewee's inference does not become the agent's historical conclusion. Store unknowns in the answer, gap/checkpoint or pending question, not a fabricated assertion. Structured date values require literal text and a kind; the helper does not interpret dates. Keep approximate years as years.

Each record operation requires an expected revision. Identical repeated turn IDs produce no changes, even after a retry; different content with the same ID fails. New turn IDs append. A correction's assertion `supersedes` lists this session's provisional conclusion IDs. Old observations and citations remain intact; old relationships become superseded. Other/dependent conclusions need the full maintenance workflow.

`action` is continue, review, pause, resume or research. Pause preserves the pending question unless the new turn explicitly changes it. Research needs a focus person; it marks a handoff ready, not a completed search. `research_question` can set a focused active question; earlier questions remain queued.

The helper creates one file and refuses to overwrite it. Record updates hold a local lock, build/validate in memory, then atomically replace the file. A crash can leave a lock: establish that no writer is running before manual recovery. Local locks are not a distributed database. Filesystem permissions, encryption, backups and access control belong to the host.

## Existing tree and reviewed cases

The agent can interview against an existing tree using its normal storage/maintenance adapter. This helper does not import or merge it. For a portable workflow, create a seed case, preserve a private mapping to existing IDs, then review a merge patch through intake and maintenance. Do not blindly replace `tree.json` or the canonical case.

Once a case contains supported/rejected conclusions, this helper refuses evidence mutations. Use maintenance to preserve old reviews, invalidate affected conclusions and perform the required GPS review. Story generation remains read-only.
