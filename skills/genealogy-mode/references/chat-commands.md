# Everyday chat commands

These are portable prompts understood by the coordinator. The plugin registers `/tree` and `/story` as native commands in Claude Code (`/genealogy:tree`, `/genealogy:story`), Cursor and Gemini CLI; in other hosts the same text works as a normal message. Users can always speak normally.

| Prompt | Skill and result |
|---|---|
| `/tree start` | genealogy-interview: start with one person, capture a first seed tree. |
| `/tree add` | genealogy-interview: add relatives, memories or leads. |
| `/tree resume` | genealogy-interview: resume the saved conversation. |
| `/tree review` | genealogy-interview: show the reported tree and gaps. |
| `/tree correct` | genealogy-interview: append a correction with history. |
| `/tree pause` | genealogy-interview: save the next question and stop. |
| `/tree research` | coordinator + planner: begin investigating the first question. |
| `/story PERSON` | genealogy-narrative: evocative history with evidence notes. |
| `/story PERSON --style documentary` | genealogy-narrative: factual biography. |
| `/story PERSON --style novelized` | genealogy-narrative: identified imagined scenes. |

Examples: “Interview me to start my family tree.” “My grandfather had another brother.” “Continue where we stopped.” “Tell Ana's life in Portuguese, like a historical novel, with imagined scenes clearly identified.”

Resolve person names against the current case and ask only when ambiguous. Reuse language, focus, scope and prior answers. User requests to research or tell a story can interrupt an unfinished interview; checkpoint it and route immediately. If returning to interview later, resume rather than restart.

Additional v1.4 prompts: “Reread this passage and replace the old reading, preserving its history.” “Generate facts and tree notes from this case.” These route to detailed reading / research-maintenance; `genealogy.py reread` records a completed reading, while `genealogy.py project` builds private derived files. Neither command invokes a model.
