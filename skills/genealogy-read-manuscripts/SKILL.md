---
name: genealogy-read-manuscripts
description: "Use when genealogy-mode or the user needs handwritten records read with four separate reading methods and reconciled. Not for typed text or a quick first pass over long files."
disable-model-invocation: true
---

# Read Manuscripts

Protocol revision: **1.4.3**.

Coordinate **four methods in four fresh contexts**. The contexts may use the same model, sequentially or concurrently. Context isolation reduces answer leakage; it does not make model errors statistically independent. Different models or human readers are optional, not a prerequisite. Never collapse to a single method merely because the model is the same. If the host can never create fresh contexts, see [Host without fresh contexts](#host-without-fresh-contexts).

Read [methods.md](references/methods.md) for packet selection and [protocol.md](references/protocol.md) for reconciliation. The research basis and technology limits are in [research-basis.md](references/research-basis.md). See [packet-helper.md](references/packet-helper.md) and use [method_packets.py](scripts/method_packets.py) to prepare faithful display variants and separate packets, retain sample provenance and summarize reported agreement; it does not run readers or decide confidence. Building image packets requires Pillow; report summarization uses the standard library. The worker briefs that methods.md hands out are the [common worker contract](references/common-contract.md), [A: stroke analysis](references/stroke-analysis.md), [B: same hand](references/same-hand.md), [C: line recognition](references/line-recognition.md) and [D: context decoding](references/context-decoding.md).

## Prepare the source and four packets

1. Resolve and inspect actual source pixels. If a remembered local path is missing, check the current attachment mapping or authorized source reference; do not repeat a stale path or pretend to have read it. Render relevant PDF pages; extracted text is not handwriting evidence. Record source ID/hash, physical page and dimensions.
2. Identify the requested entries, continuations, insertions and margins. Assign stable region IDs and original-pixel bounding boxes. Do not let a crop force one segmentation of a disputed word.
3. Register each original page with its source ID, page identity, SHA-256 and archival locator. Use packet schema 1.2 to derive crops from the verified frozen page. Optional supplied crops must match those pixels exactly; dimensions alone cannot establish correspondence. Preserve original page bytes. Never generate, inpaint or reconstruct missing strokes. Reject unsupported high-depth modes until a documented display conversion is available.
4. Prepare neutral original plus enlarged target/line views before launching methods. Never rely on a 150-pixel word or a reduced whole-page preview. Tile enlarged long lines with at least one line height of overlap, and use `display.margin` when a tight box cuts letters. Do not use contrast, sharpening or denoising views: compression blocks can masquerade as ink. Preserve source/page/sample identity, hashes, coordinates and transformation records. Enlargement adds no source detail.
5. Prepare different evidence scopes: local crops for morphology; target plus marked line position, preceding-word crop and same-hand examples for comparison; complete lines for sequence reading; full entry/page **and line/target close-ups** plus verified clues for contextual decoding. Supply a preceding-word bounding box or explicitly mark a target at line start. Each exemplar needs its own source/page/sample/bounds; retain those identities when merging overlapping views. Reuse a shared page once within a method's packet.
6. Build draft packets, then inspect the frozen original page, every target's neutral original/enlarged views and B's marked line locator in the actual viewer. Check source/page identity, complete word/phrase boundaries, preceding anchor and usability; record exact inspected paths, reviewer/context, timestamp, booleans, source quality and concrete notes using `record-preflight`. Pixel matching cannot tell whether the intended word was selected. Never tick checks without inspecting. A failed check or `needs_better_source` blocks dispatch; repair and rebuild in a fresh directory.
7. Run `dispatch` only after the recorded preflight passes. It rechecks the frozen inputs and releases one scoped folder with a receipt per method. Give each fresh context only its released folder, never a draft folder or coordinator manifest. A method may abstain when its evidence is absent; do not substitute another unrestricted read. The helper enforces its release path, not filesystem isolation or the truth of an operator's assessment.

| Method | Input boundary | Required evidence product |
|---|---|---|
| **A: stroke and grapheme analysis** | Local target crops; script metadata only | Observable feature inventory and uncertain character sequences |
| **B: same-hand exemplar matching** | Target, marked line position, preceding word and same-hand material | Fixed target location plus exemplar correspondences, locators and counterexamples |
| **C: whole-line sequence recognition** | Complete lines and target details; no external genealogy or place list | Frozen raw line output, diplomatic transcription, character audit and actual recognizer metadata |
| **D: contextual constraint decoding** | Full entry/page, line/target details and verified contextual references | Candidate/constraint table separating visible letters from contextual additions |

These are distinct strategies, not four versions of “read this carefully.” A and B are palaeographic analyses. C uses an available suitable HTR engine or an explicitly labelled whole-line vision-model pass; a prompt does not implement CTC, TrOCR or an HMM. D applies linguistic and documentary constraints without rewriting contrary ink. Do not download models or transmit private scans just to satisfy a method label.

## Keep contexts separate

- Use `fork_turns="none"` or equivalent fresh calls. The same model can perform all four. One concurrency slot means four serial fresh contexts, not one inherited conversation.
- Do not tell a method worker about the other workers, their existence, candidate readings, quorum policy or earlier answers. Do not send this SKILL.md, the full methods index or coordinator notes to a worker.
- Give only that worker's contract, brief, page-qualified input paths and neutral metadata. Permit faithful viewing derivatives in its private `work/` directory, with transform records; keep shared inputs immutable. Keep prior transcriptions and user suggestions privately as hypotheses. D alone may receive verified contextual clues; record their provenance and exclude target-reading-derived clues from its initial packet.
- Require final-message reports. Prohibit workspace searching, session enumeration, delegation and external communication. Shared files remain a procedural contamination risk, not a security boundary; record any leakage.
- If fresh contexts cannot be created, or a report shows `context_isolation` other than `fresh`, no context ID, or a context ID another method also used, stop. The four-method panel cannot run, and comparing such reports would look valid without being valid. Say so plainly and switch to the blind plus context double reading: first one blind visual reading from the target and line crops only, with no verified context, earlier transcripts or user suggestions, frozen before anything else is shown; then one context reading that adds the verified context and records which letters the context changed. Label the result a double reading in one context, never four-method agreement. You may leave the four packets ready for a host that can run them later. `method_packets.py summarize` refuses such reports with this error. Do not fabricate fresh contexts, abandon methods merely because they share a model, or claim a blind panel ran.

## Host without fresh contexts

Some hosts can never start a fresh context, for example an agent that cannot start subagents or make fresh calls. On such a host:

- **What to do.** Do not run A, B, C and D one after another in your own context, even if you label them `shared`. Stop the four-method panel, tell the user why, and do the blind plus context double reading above. Return that reading. Then offer a way to get a real panel: hand the user the four released packets to run in separate fresh contexts somewhere else, or ask a human reader to check the consequential words. Record which one the user chose, if any.
- **What it does to the result.** A fallback reading is weaker than a panel. Only one reader looked at the letters, and the context reading saw the blind one. Label it "double reading in one context" and name the host limit in its report. Never report it as four-method agreement, as a panel, or as `visually_supported`: its highest confidence is tentative, because there is no separate A/B letter evidence to audit against. Only a later real panel or a [recorded human check](references/protocol.md#recorded-human-check) can raise it.
- **When a quick read already happened in this context.** The blind reading is not blind, because you have already seen a reading of the same words. Label it "context reading after a quick read" instead of blind, and the result "double reading in one context, not blind". In the `reading_method` block, record the first reading as `not_blind` and the second as `context`, both with `context_isolation=shared`. A quick read done in another context whose text you have not seen does not count against blindness.

## Execute and reconcile

Use the default three-round limit, including round one. Start all four methods only on a bounded batch that passed preflight. Missing same-hand exemplars justify B abstention. If the limiting factor is missing source pixels, stop and request a higher-resolution archival scan; another reader round on the same JPEG is not an intervention. A specialized HTR model is optional; if unavailable C remains a whole-line vision-model reading with the actual implementation disclosed. A failed engine call is not a result.

Freeze every report before inspecting/combining them. Validate method compliance: A must supply local features, B real exemplar locations, C an actual line reading/engine result, D explicit constraints and visible-versus-inferred distinctions. Generic identical prose from four contexts is not evidence of four methods applied. Request a format correction or record noncompliance; never invent the missing product.

Align readings by source coordinates, preserving spelling, accents, segmentation, abbreviations and alternatives. Record agreement by **method**, actual context IDs, model/tool identities, shared priors and clues. Report “A/B/C/D agree” only as observed agreement. Do not call 4/4 a probability, count alternative candidates as votes, or label same-model agreement independent corroboration.

Apply the protocol's mandatory `sequence_letter_audit` to consequential C readings, comparing initial/medial/final characters and boundaries with A/B evidence and the source close-up. Missing A/B evidence is not agreement; fluency cannot clear a letter conflict. Inspect material names, places, ages, dates, sums, kinship and negation yourself. Assign confidence from legibility, discriminating visible features, justified exemplar matches and unresolved conflicts under the protocol. A plausible local name must not displace visible uncommon spelling. Agreement cannot repair missing ink or demonstrate a real-world identity.

## Follow up and deliver

Record actual method calls and any known usage, and distinguish display/preparation failures from unreadable ink. Four methods have no established advantage over a blind-plus-context baseline. Fix unusable packets before paying for four calls.

Rerun only methods/regions that can benefit from a specific new input: wider crop, better scan, verified same-hand example or sourced contextual fact. Use fresh contexts again; never forward peer answers or majority suggestions. Keep the initial reports and each clue's provenance. A later report replaces that method's current report; it is not another vote. Mark context-assisted convergence. Stop without a forced winner when no new discriminating evidence exists.

Return a diplomatic transcription, material uncertainty table, source/region references and a brief methods note. Keep modernized readings or translations separate. Use `[word?]`, `[a / b]` and `[illegible]` (or PT-PT equivalents); reserve `[…]` for intentional omissions. State methods completed/abstained, contexts actually used, shared model limitations and any real HTR tool used. Present the four-method detail only where it helps the user assess uncertainty.

In the genealogy suite, preserve the immutable processing run and use the v1.4 reread/supersession workflow for corrections. Transcription confidence never promotes a genealogical conclusion by itself. Do not infer authorship, parentage, motive or later events beyond the source.
