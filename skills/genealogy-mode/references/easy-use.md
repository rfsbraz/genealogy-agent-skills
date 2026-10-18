# Everyday interaction

Use one entry point: genealogy-mode. Choose specialists internally. The user should not need to understand the skill catalogue, database schema or genealogy vocabulary to begin.

## Three starting requests

- **Research someone:** use the person, question and any supplied evidence. If no question is specified, choose the nearest useful gap and explain the choice in one sentence.
- **Read this document:** choose quick reading for orientation or large documents; detailed reading for decisive passages and explicit detailed requests. Record the exact page coverage. Do not imply that unreviewed pages were read.
- **Show progress / continue:** read the checkpoint and actual ledger, report what changed and continue the next authorized action. Do not restart intake.

## Default experience

1. Read available material before asking questions. Start with one person or document, one question and one useful action. Accept rough dates, partial names and uncertainty.
2. Ask at most one short blocking question at a time, preferably with a few understandable choices. Ask nothing if existing material suffices. Do not make the user complete the data model or approve routine internal plans.
3. Default to a brief explanation and a bounded useful research batch. Infer language from the user; retain original-language source text and explain specialist terms once in ordinary language.
4. Handle source discovery, citations, mention IDs, page accounting, conflicts and GPS records internally. Never omit a material uncertainty to keep the answer short.
5. Default to the three most useful source leads, each with why it matters and the next action. Keep the broader portfolio in the case. The three-lead display is not a research stopping rule.
6. End with a short progress card: **Finding**, **Why**, **Still uncertain**, **Next step**. Include precise citations near findings and a saved audit path. Omit empty fields. Aim for roughly 150–250 words unless the user requests more or the findings need it.
7. Offer fuller evidence detail when useful without requiring another turn to complete already authorized work. A request for a full report overrides the brief default.

## Wording

| Internal state | Everyday wording |
|---|---|
| supported + current GPS review | Supported by reviewed evidence |
| source_supported | Supported by the cited evidence within the stated scope; full review pending |
| provisional | Working lead |
| unresolved | Not yet established |
| rejected + current GPS review | Ruled out for this question |
| superseded | Earlier conclusion, since revised |
| legacy conclusion without GPS review | Previous conclusion; review still needed |
| inaccessible | Source not accessible in this session |
| no_match | No match within the stated search coverage |

State the reviewer type if asked about review: agent, self-review or human. Never imply a human reviewed an agent result. A completed reading task, high OCR confidence and a supported family relationship are different things.

## Accessibility

Use meaningful link labels and text status labels. Do not rely on colour, symbols, diagrams or wide tables to convey essential information. Use short paragraphs and numbered steps for tasks. Every workflow diagram must have an equivalent prose path. Keep original names and diacritics; provide transliteration as an additional field, not a replacement. Avoid unexplained acronyms and raw JSON in ordinary conversation.

This is an interaction contract for a host agent, not a shipped graphical interface or a claim of WCAG conformance. Evaluate it with task completion and observed user behaviour.

## Consent and interruptions

Reuse authorized scope. Prepare the exact message/order before requesting any missing authority; never turn routine searching into an approval ceremony. Do not send, spend or publish merely to simplify the experience. Explain a genuine blocker in one sentence, record it, and continue independent work. A short user correction updates the active case; it does not erase evidence history.

## Interview and story modes

For a conversational start, use genealogy-interview, asking one useful question at a time. For an evocative or novelized life story, use genealogy-narrative; its requested length overrides the short progress-card default. See chat-commands.md for optional shortcuts. Do not make the user learn the command syntax or prepare machine-readable data.
