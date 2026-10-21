---
name: genealogy-narrative
description: "Tell an ancestor's life as a readable historical narrative with period atmosphere, flourish and traceable evidence. Use for /story, family chronicles, romantic or evocative biographies, and explicitly novelized reconstructions. Separate records, recollections, inference, historical context and invented scenes."
---

# Tell a Family Story

Read the coordinator's [shared contract](../genealogy-mode/references/shared-contract.md), [writing guide](references/writing-guide.md) and [story contract](references/story-contract.md). This is presentation over evidence. It does not change conclusions or count generated prose as a new source. Those files point on to the coordinator's [GPS policy](../genealogy-mode/references/gps-policy.md) and [easy-use rules](../genealogy-mode/references/easy-use.md); read them when the task touches them.

## Start with the person

Resolve the person from the current tree; ask one short disambiguation only if needed. Read current case/source data before chat summaries. Gather the timeline, relationships, source assertions, reviewed conclusions, recollections, conflicts and gaps. Include everyday details, not just milestones.

Do not require a style questionnaire. Follow requested language/length; otherwise use the user's language, evocative style and about 700–1,000 words when evidence permits. With sparse evidence, write a shorter vignette. “Everything we know” means a coherent story plus an appendix for details that interrupt it, not filling every gap.

## Choose a style

- **documentary**: factual biography with literary phrasing and attributed recollections/inferences. No invented scene, dialogue, feeling or sensory event.
- **evocative** (default): historical narrative with rhythm, imagery, researched period context and evidence-based possibilities. Signal inference naturally: “perhaps”, “may have”, “the records suggest”. Do not invent weather, clothing, journeys, dialogue, emotions or motives as actual experiences. Specific atmosphere must be sourced, or explicitly imagined in novelized mode.
- **novelized**: when requested, add clearly identified imagined scenes, sensory details, inner thoughts or dialogue. Label the work historical fiction/reconstruction and identify imagined paragraphs in notes. Explicit fictionalization requests authorize this; do not ask again. Romantic/epoch prose alone does not imply an invented love affair.

Never invent consequential biographical events or relationships inside a researched life story: parentage, partners, children, crimes, diagnoses, migrations or causes of death. A requested different fictional life must be labelled alternate fiction outside the genealogy record. Do not fictionalize sensitive allegations about real people.

## Compose

1. Build a source-linked brief. [story_tools.py](scripts/story_tools.py) can inventory one person's evidence read-only; inspect actual artifacts as needed. Its brief does not certify that statements are true.
2. Choose a human thread grounded in the evidence: work, belonging, migration, care, loss, continuity or an unanswered question. Do not invent a motive to force a plot.
3. Research relevant local/period context with available tools and cite inspected sources. National history does not prove individual participation. Check dates, boundaries, objects, transport and customs; avoid stereotypes. If research tools are unavailable, omit unverified specifics.
4. Write an opening, a life arc and an ending that acknowledges what survives and what remains unknown. Use concrete record details, varied sentences, restrained metaphor and accurate period vocabulary. Never fabricate archival quotations or references.
5. Classify each paragraph as documented, recollection, inference, context or imagined in a separate story manifest. Split mixed paragraphs when necessary. Small note markers keep the prose readable while identifying its basis. A blanket disclaimer alone cannot identify specific inventions.
6. Audit names, dates, relationships, quotations and historical details. Keep material contradictions visible in prose. Do not smooth uncertain parentage or identity for the plot. Describe conclusions as supported only if their GPS review is current; observations can be narrated as “the register records” or “the family recalls”.
7. Deliver the story followed by “Behind the story” notes: documented material with citations, attributed recollections, reasoned inference, context and imagined passages. Include unresolved questions. Save the story manifest and evidence fingerprint separately from the case.

## Preserve the research boundary

Never write invented or contextual details into person facts, events, observations, hypotheses or proof reviews. Store narratives in a private stories area by default. Public sharing requires existing authorization and privacy review; the helper does not publish. Recheck a story when its evidence changes. A rerun is not independent evidence.

The helper checks classifications, references, fingerprint and selected safeguards. It cannot judge truth, the strength of inference, sentence-to-source support or complete privacy. Perform a semantic editorial review. Its renderer emits Markdown with notes; it does not run a model or write prose for you.

## Resources

- [Writing guide and examples](references/writing-guide.md)
- [Story contract and commands](references/story-contract.md)
- [Story schema](assets/story.schema.json)
- [Story template](assets/story-template.json)
