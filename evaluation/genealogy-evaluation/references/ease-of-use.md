# Measure ease of use alongside research quality

Use paired tasks with the same evidence, model, tools and budget. Retain raw conversations and tool traces; use a fresh case for each run. Assess beginners and experienced researchers separately. These targets are proposed release goals, not measured population statistics.

| Task | Expected usable behaviour | Measure |
|---|---|---|
| Start with a family recollection and no precise origin | Choose one useful evidence-seeking step without demanding a full intake form | Turns until useful action; unnecessary questions; user completion |
| Receive a 250-page document | Offer quick orientation, record actual coverage, escalate decisive passages | Time/tokens to useful page shortlist; coverage correctness |
| Ask for a short answer on contradictory parentage | Give an understandable unresolved finding and next step | Unsupported accepted links (must be zero); visible uncertainty; user comprehension |
| Resume a saved case | Continue the checkpoint without repeating completed work | Repeated questions/searches; turns to resume |
| Discover an unlisted country | Continue official/local discovery without guessing source coverage | Valid next step; no false claims of searches or availability |
| Ask why a claim is supported | Show the evidence and reasoning with precise citations | Traceability; ability to identify the relevant source passage |

Default conversational targets: one short blocking question at a time, a useful first response, no unexplained internal IDs/JSON, and roughly 150–250 words for a brief progress request. These are presentation targets, never grounds for hiding contradictions or truncating requested detail. A longer answer may be appropriate; human reviewers should score whether it helps the task rather than reward a rigid word count.

Accessibility review: meaningful link text; text labels for every status; essential content available without a diagram or colour; readable paragraphs; original names preserved; technical terms explained. This package contains instructions and CLI helpers, so a host UI needs its own keyboard, screen-reader and WCAG testing.

Do not claim ease of use from code tests alone. Report observed task completion, user comprehension and requests for help separately from synthetic agent trials. Compare concise and detailed modes without weakening GPS requirements. Do not average a false accepted parentage link away with good usability scores.
