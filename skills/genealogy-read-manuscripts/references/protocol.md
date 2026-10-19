# Coordinator-only evidence reconciliation

## Keep separate records

For each region keep immutable method reports, exact input hashes, actual context IDs, model/tool/checkpoint identities, execution kind, round, supplied clue IDs and limitations. Record `context_isolation` independently of `model_diversity`: four fresh contexts running one model satisfy the intended workflow, while retaining shared-model error risk.

Maintain:

- `initial_reports`: A/B/C/D results, including abstentions or blocked work;
- `candidate_groups`: exact literal first-choice agreement by method, separate alternatives;
- `evidence_matrix`: local features, exemplar correspondences, line structure and contextual constraints for each candidate;
- `visual_quality`, `material_field`, unresolved strokes/diacritics/segmentation and opposing evidence;
- `clues`: ID, fact, source locator, why it is established without assuming the disputed reading, its certainty (`certain`, `probable` or `uncertain`), recipients and round;
- `later_reports`: method, round, prior report ID, new inputs and changes;
- `final`: reading, confidence label, concrete reason, context-assisted flag and stop condition.

Only normalize Unicode composition and outside whitespace when comparing literal strings. Do not merge historical/modern spellings, accents, name variants, word boundaries or expansions. Keep output words aligned by source region rather than by the similarity of generated sentences.

## Carry the method record forward

After the reading, keep a record of how it was read next to what it says. Build one `reading_method` block from the frozen reports. Put it in the run's `finish` metadata and on each observation the reading supports; generated fact rows copy it from the observation. The block has a `methods` list with one entry for each method that ran:

- `method_id`: `A`, `B`, `C` or `D` for the panel, `single` for one reading, or `blind` and `context` for the double reading in one context. Use `not_blind` instead of `blind` when a quick read already happened in the same context, so the record shows that the first reading was meant to be blind but was not.
- `context_isolation`: `fresh`, `shared` or `unknown`.
- `context_id`, `model_identity` and `execution_kind`: copied from the report, including `unknown` and `host-default-unspecified`.
- `status`: `completed`, `partial`, `abstained` or `blocked`.

The block records what ran. It does not make the reading more or less reliable. A host that has only a free-text field can store the same block as one line:

```text
reading_method: method_id=A, context_isolation=fresh, context_id=ctx-example-a, model_identity=host-default-unspecified, execution_kind=visual_feature_analysis, status=completed; method_id=B, context_isolation=fresh, context_id=ctx-example-b, model_identity=host-default-unspecified, execution_kind=same_hand_comparison, status=abstained; method_id=C, context_isolation=fresh, context_id=ctx-example-c, model_identity=host-default-unspecified, execution_kind=vlm_line_reading, status=completed; method_id=D, context_isolation=fresh, context_id=ctx-example-d, model_identity=host-default-unspecified, execution_kind=contextual_decoding, status=completed
```

For a double reading in one context, not blind, the line is:

```text
reading_method: method_id=not_blind, context_isolation=shared, context_id=ctx-example-shared, model_identity=host-default-unspecified, execution_kind=visual_reading, status=completed; method_id=context, context_isolation=shared, context_id=ctx-example-shared, model_identity=host-default-unspecified, execution_kind=contextual_decoding, status=completed
```

Separate methods with `;` and fields with `,`. Write each field as `name=value`. Values cannot contain `;`, `,` or `=`. Parse the line back into the block before you check or project it.

## Recorded human check

A fallback double reading on a host without fresh contexts is capped at `tentative`. A later real four-method panel can raise it. So can a **recorded human check**. This section defines that check. Without one (or a later panel), the `tentative` ceiling stands.

### Who counts

A named human reader. The user of the session counts. An agent in another conversation does not, even if labelled as a reviewer. Record the person's name or handle as they give it; do not invent one.

### What they check

Only the consequential words: names, places, ages, dates, sums, kinship and negation that decide the reading. They check those words against the frozen target and line crops from the packet, not against a reconstructed page or a later edit. Ideally they see the crops before seeing the agent's reading. If they already saw the agent's reading, record that fact.

### What gets recorded

Store one `human_check` object next to `reading_method` on the run and on each observation the reading supports:

- `reviewer`: name or handle of the human
- `reviewed_on`: ISO date, or `unknown` when the date was not kept
- `words_checked`: the consequential spans they looked at
- `confirmed_reading`: the text they confirmed, or the corrected text if they changed it
- `saw_agent_reading_first`: `true` or `false`

A host that has only a free-text field can store the same object as one line:

```text
human_check: reviewer=Example Reader, reviewed_on=2026-10-19, words_checked=given name and surname, confirmed_reading=Example Name, saw_agent_reading_first=false
```

Separate fields with `,` and write each as `name=value`. Values cannot contain `,` or `=`. Parse the line back into the object before you check or project it.

### Where the host stores it

Put `human_check` alongside `reading_method` in the run's `finish` metadata and on the observation. The local queue and case schema do not yet validate this field. Until they do, the host keeps the object (or its one-line form) in those same places using whatever free-form metadata or observation property it already accepts. Do not drop the check, and do not invent a second authority for it.

### What it allows

After a recorded human check that confirms the consequential words against the frozen crops, the reading may reach `visually_supported`. If the reviewer corrects the text, use their `confirmed_reading` and keep the check on the corrected observation. If they saw the agent's reading first, still allow `visually_supported` when they confirm from the crops, but the report must say they saw the agent reading first. Without a recorded human check or a later real panel, a fallback double reading stays at most `tentative`.

### Request template

When you need the check, send the user one message in this shape (fill the brackets):

```text
Please check these consequential words against the frozen crops (not against my reading if you can avoid it):
- Words: [list]
- Crop paths: [exact paths]
- My current reading (look only after you have decided, or skip): [text]

Reply with: your name, the date, each word you checked, the reading you confirm or correct, and whether you saw my reading before deciding.
```

## What an agreement count means

Use “four methods agree in separate contexts, same model” when that is what happened. Never say four independent witnesses, independent corroboration, 100% confidence, or that method diversity establishes statistical independence. A/B/C share pixels; D may share the same model's language priors. A different engine is a different recognizer, not another historical source.

| Observed pattern | Consequence |
|---|---|
| 4/4 agree | Inspect the proposed text against pixels; check that each method produced its distinct evidence product. Agreement alone confers no confidence level. |
| A/B/C agree; D differs | Determine whether D exposes a missed word/abbreviation or merely prefers a familiar formula/name. Resolve from source evidence or retain both. |
| Context favors a candidate without discriminating ink | Keep it as a contextual candidate, with uncertain literal text. |
| 2/4 or 3/4, with direct visual disagreement | Preserve the viable alternative and target the disputed feature; no majority override. |
| One method or several abstentions | Report exact coverage and missing evidence. A clear visible reading can still be useful, but has less method cross-checking. |
| Agreement only after a shared clue | Label context-assisted agreement; retain the initial pattern. |
| Four generic repeats or leaked answers | Record method noncompliance/contamination, not four-method agreement. |

Always retain the planned denominator of four when reporting coverage; separate completed, partial, abstained and blocked methods. Count one current report per method. New rounds and alternative candidates never add votes. A mere suggested reading is not a literal vote when internal letters remain unresolved.

## Mandatory sequence-reading check

After blind reports are frozen, compare every consequential C candidate against the original/enlarged target and A/B's actual evidence. Keep C's raw line output immutable. Build a `sequence_letter_audit` for the candidate with character/group, page-qualified source/view locator, observed form, A finding, B finding, conflicting evidence and coordinator disposition. Inspect the initial letters, medial groups, ending, abbreviation marks and boundaries explicitly. An invented plural ending or a fluent replacement name cannot survive on contextual fit.

If A/B are incomplete, obtain the missing letter evidence from the source; their abstention is not agreement. If the source cannot resolve the difference, retain uncertainty or reject the candidate. Do not label it `visually_supported` while a material discrepancy remains. C's own confidence, whole-line fluency, engine scores and D's semantic fit cannot clear this check. If a clear source feature refutes a candidate, record why it was rejected rather than treating every guess as equally viable. The summarizer exposes a pending sequence-check queue, not an automatic approval.

## Confidence from evidence, not votes

- **Visually supported:** the consequential characters and boundaries are adequately visible; the coordinator can state their discriminating features or secure exemplar matches, and no substantive conflicting visual evidence remains. Show any harmless orthographic ambiguity separately. Method agreement can support the audit trail but cannot create this label by itself.
- **Tentative:** there is a defensible reading, but viable alternatives, uncertain marks/boundaries or material conflict remain. Display the ambiguity in the transcription.
- **Contextual candidate:** context suggests wording that the image does not establish. Keep the literal span uncertain and the suggested completion separate.
- **Unreadable:** there is insufficient defensible visual evidence even for a preferred literal candidate.

For names and places, explicitly test the uncommon reading against the familiar one; do not normalize to the local gazetteer. For dates/ages, distinguish similar digits and calendar/event meanings. For negations/kinship, inspect short omitted words and abbreviations. Without a human-reviewed reference set, do not provide calibrated probabilities or claim measured improvement.

## Targeted rounds and admissible clues

Round one uses four separate method contexts with different evidence scopes. D's initial source-verified contextual material is logged; the other methods do not receive it. User suggestions and old transcripts remain private hypotheses.

For a later round choose an intervention that could resolve a specific uncertainty: wider uncropped boundaries, better-resolution original, a separately legible same-hand exemplar, or independently documented language/genre/place context. A clue cannot be proved by agreement on the target reading itself. Do not send the preferred candidate, majority count, peer arguments or old transcript to a method worker. If it is useful to test an explicit prior reading, do so as a separately labelled comparison after the blind reports are frozen, outside the initial agreement count.

Fresh contexts may again use the same model. Rerun only the relevant methods/regions and preserve earlier outputs. Record whether a clue changes the scope from visual-only to contextual. Retract a disproved clue and reassess affected results. Default to three rounds total, stopping earlier when evidence is adequate or when no new input can distinguish candidates. Do not keep sampling the same prompt until a majority appears.

## Input quality and cost

Use packet schema 1.2 to register and hash original pages, freeze their bytes, and derive crops at the stated coordinates. Optional supplied crops must match the frozen page pixels exactly. This establishes pixel correspondence, not that the intended complete word was selected. Unsupported high-depth image modes fail explicitly rather than clipping ink during conversion.

Inspect every target's required files in the actual viewer: frozen page, neutral target original/detail and B's marked line locator. Check page identity, complete boundaries (including short preceding words), the preceding-word anchor and usable detail. Fill the generated preflight template with the exact inspected files, reviewer/context, timestamp, boolean checks, source-quality decision and concrete notes. Never auto-fill a pass from successful image decoding. `record-preflight` saves the assessment; `dispatch` rechecks it and all frozen hashes before releasing method folders. Missing checks, changed inputs and `needs_better_source` block release. Rebuild corrected inputs in a fresh directory. The helper enforces recorded checks in its workflow, not honest visual judgement or OS-level isolation.

Keep neutral originals/enlargements only. Contrast and sharpening can amplify JPEG blocks into false strokes. D reuses a shared page once; B receives a marked line position and preceding-word crop before exemplars, with duplicate sample coverage merged but page-qualified aliases retained. Ensure B's reported `target_location` is the requested region; an exemplar cannot relocate the target to another word in the line. A valid schema is not sufficient: inspect its anchor reading and actual correspondences.

Do not spend four calls diagnosing unreadable input. Repair a missing view first, or report that better source pixels are needed. Classify failures as preparation/display, method abstention or unresolved source text. When the source resolution is exhausted, request the archive's higher-resolution original with its image identifier; do not repeat readers on the same JPEG. Build a new versioned packet only after new discriminating evidence arrives. A failed region can be excluded into a separate blocked record while preparing a fresh packet for genuinely usable regions.

Record actual calls and available usage/cost; keep unknown costs unknown. Compare resolved spans and material errors with a blind-plus-context baseline only where such a comparison exists. Four methods are the requested workflow, not a demonstrated accuracy or cost advantage. User-reported field feedback found no gain in v1.4.1, then improved readings with corrected crops in v1.4.2; the latter still had unresolved fields and a gazetteer-assisted candidate. Neither is a controlled accuracy benchmark.

## Runtime and technology honesty

One model with four fresh contexts is the normal supported configuration. One active slot can run the contexts sequentially. If the host has only one persistent context and no fresh-call facility, the four-method panel cannot run: do not run the four methods in that one context. Stop, say so, and use the blind plus context double reading described in SKILL.md, or leave the separate packets ready for a host that can execute them. `summarize` raises an error instead of warning when any report lacks a fresh, unique context. Never report unexecuted contexts or claimed engine runs.

`method_packets.py` builds scoped files and produces descriptive agreement summaries. Its source checks verify crop/page pixel correspondence; hashes bind files and review records. They do not verify intended-word selection, transcription truth, clue correctness, context isolation or genuine method compliance. The coordinator must inspect the report contents and pixels. The helper never assigns a confidence label.
