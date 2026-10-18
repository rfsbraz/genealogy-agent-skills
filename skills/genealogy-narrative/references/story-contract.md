# Story contract

## Invocation

Normal language works: “Tell Ada's life as a historical story”, “Write a factual biography”, or “Make a clearly novelized version with imagined scenes.” Optional chat conventions:

- `/story Ada`: evocative historical story.
- `/story Ada --style documentary`: factual biography with evidence notes.
- `/story Ada --style evocative`: literary prose and supported inference.
- `/story Ada --style novelized`: identified imagined scenes within the known life.

Names are resolved by the agent; ambiguous names require one clarification. Optional language, length and audience may be supplied in ordinary language. These are chat conventions, not installed native slash commands or a model-running CLI.

## Files and helper commands

From this skill directory:

```sh
python scripts/story_tools.py brief /private/family/case.json --person P-ADA --out /private/family/stories/ada-brief.json
python scripts/story_tools.py check /private/family/case.json /private/family/stories/ada.story.json
python scripts/story_tools.py render /private/family/case.json /private/family/stories/ada.story.json --out /private/family/stories/ada.md
```

The root package exposes these as `genealogy.py story ...`. A host agent writes the prose and manifest using `assets/story-template.json`. The empty template is intentionally not a valid finished story. `brief` provides relevant evidence and flags structural/GPS review issues; it does not write a biography. `check` inspects only the documented contract. `render` creates a new Markdown file and refuses overwrite.

The case remains schema 1.1. Story manifests use their own schema 1.0 and stay outside the case, with the source case ID, person ID and evidence digest. No story text is imported into the proof graph. A changed case digest blocks rendering until the agent reviews affected passages and records the new fingerprint; do not merely refresh the hash to bypass review. Retain older story versions when revising.

## Paragraph classification

| kind | basis | Required support / phrasing |
|---|---|---|
| documented | record_statement | Observation with full citation; phrase as what the record states. It need not be proven historically true. |
| documented | reviewed_conclusion | Current supported conclusion(s) with complete GPS review checks. |
| recollection | attributed_memory | Cited testimony/recollection; identify who remembered or reported it. |
| inference | reasoned_inference | Observations/conclusions/context and a reasoned note; signal uncertainty in prose. |
| context | historical_context | Inspected contextual source with locator, date consulted and locality/period scope. Do not claim the person participated. |
| imagined | fiction | Novelized mode, visible overall fiction notice and an explanatory passage note. No historical citation attached to the invented passage. |

Each paragraph has stable `id`, `text`, `kind`, `basis`, evidence/context ID lists and `note`. Split mixed passages into separately classified paragraphs. Link citations through observations/conclusions, not invented citation IDs. Context sources are additional sources consulted for the narrative and remain outside person facts. Story notes use small numeric markers; the renderer places full citations under “Behind the story”.

All helper outputs are private working artifacts. A requested public version needs a separate authorized, redacted publication workflow. The private flag and footer do not enforce access control. The checker cannot detect every living person, sensitive detail, false inference or invented statement hidden inside a paragraph labelled documented. Human/agent semantic review is required.

## Acceptance and handoff

Deliver the story, its basis notes, unresolved questions, and a private manifest when storage is available. Record the actual research/context work performed and omissions. For a website, retain provenance in a private sidecar; public notes can expose only information allowed for that audience. Hand new genuine research findings to extraction/proof evaluation separately before updating the case and rerendering the story.
