# Interview protocol

## Optional chat shortcuts

| User says | Behaviour |
|---|---|
| `/tree start` / “Help me start my tree” | Start with a person or relative; reuse supplied information. |
| `/tree add` / “Let me tell you about my aunt” | Capture more people or memories in the current case. |
| `/tree resume` / “Continue the interview” | Load the checkpoint; ask only the saved next useful question. |
| `/tree review` / “Show what you have” | Show a compact tree/list, reported facts, gaps and corrections. |
| `/tree correct` / “I got that date wrong” | Append a correction; preserve the superseded assertion. |
| `/tree pause` / “Enough for now” | Save the pending question and stop interviewing. |
| `/tree research` / “Start investigating” | Hand available evidence and one question to the coordinator. |

These are conversational conventions interpreted by the agent, not globally registered commands. Normal language is sufficient. The agent must not ask the user to prepare JSON.

## Choose the next question

Use the smallest question that advances this user's goal, not a rigid questionnaire. Keep a queue internally; show only one question. A user may supply a whole family in one reply: extract it all before deciding what is missing.

1. **Focus:** who to start with. Accept “me”, “my grandmother” or “the man in this photograph”. Use a descriptive label if the name is unknown.
2. **Connection:** how the person relates to the user or another known person. Do not assume a biological relationship from “raised me”.
3. **Time/place anchor:** one approximate event, place of residence, marriage, death or migration. Ask the missing dimension that most narrows the search. Never convert “from Porto” automatically into birthplace or civil parish.
4. **Family cluster:** parents, partners, siblings, children or a neighbour, as relevant. Do not require all generations. Keep namesakes distinct.
5. **Basis:** ask “How do you know that?” when an important recollection needs interpretation. Record firsthand memory versus who told whom. User confidence is not proof.
6. **Available material:** suggest a certificate, photo inscription, letter, family book or precise archive reference likely to help. A user mentioning a document does not mean the agent has read it.
7. **First question:** turn the user's interest into one answerable question and begin research. Stop intake when enough exists to act.

Do not infer origin, ethnicity, religion or nationality from surname alone. An uncertain country stays uncertain. Once a relevant place/period appears, use country-independent origin and repository discovery. Country starters are hints, not mandatory providers.

## Unknown, skip, conflict and correction

- “I don't know”: save the gap; choose another anchor. Do not invent a value or repeat the same question next turn.
- “Skip”: remember the skipped topic. Revisit only if the user reopens it or a later task genuinely requires explaining the blocker.
- “1910, perhaps 1912”: keep alternatives or an explicitly uncertain range, without manufacturing a midpoint birthday.
- “José raised her”: record the wording; ask about relationship type only when needed. Never silently make him her biological father.
- A correction: preserve both utterances; supersede the specific claim. Reassess dependent relationships through maintenance.
- Conflicting relatives: attribute both accounts. Do not choose the more confident speaker or count repeated hearsay as independent evidence.

## Example conversation (all people fictional)

User: “Start with my grandmother Ada Vale. Born around 1910, no idea where. Her brother was Leo.”

Agent: “I have Ada and her brother Leo, with Ada's birth year still approximate. Do you know a place where Ada lived?”

User: “Vale da Serra. Leo was adopted by another family, I think.”

Agent: “I'll keep Vale da Serra as a place she lived, and Leo's adoption as an uncertain family recollection. Do you have a record or photograph connected with Ada?”

Do not ask for Ada's name, exact birthday, both parents and permission to continue in the same response.

## Handoff packet

Save the case, raw turns, citations, provisional persons/relationships, uncertainty, candidate places, inspected artifacts and uninspected leads. Show a short current family view with explicit “reported” links. Choose one research question and up to three next actions with reasons; note what would unblock each. Research may start before every interview topic is complete.
