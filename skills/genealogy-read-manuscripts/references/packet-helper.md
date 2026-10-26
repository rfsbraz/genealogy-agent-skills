# Scoped packet helper: schema 1.2

Contents: [inputs](#register-pages-and-targets), [views](#generated-views), [preflight](#record-the-visual-check-and-release-inputs), [reports](#run-and-reconcile), [migration](#migration).

Use `scripts/method_packets.py` to build, review and release scoped inputs. Building needs Pillow and Python 3.10+; review, dispatch and summarization use the standard library. The helper does not invoke models, acquire scans or compute transcription confidence.

## Register pages and targets

Resolve actual readable files; never reuse a missing path from another environment. Register every full page used by a target or exemplar with its SHA-256 and archival locator. Hash the bytes actually inspected. Use physical image/page identities consistently: page `1` and `"1"` cannot be mixed.

Render multipage files into correctly oriented individual pages first; retain the source and document rendering/rotation. Supported modes are 1, L, LA, P, RGB and RGBA. High-depth/other modes are rejected; preserve the original and prepare a documented display conversion instead of silently clipping tonal values. Never reconstruct ink.

Example specification beside the images (replace hash placeholders with actual SHA-256 values):

```json
{
  "schema_version": "1.2",
  "source_id": "S-001", "script": "Latin", "round": 1,
  "pages": [
    {"source_id": "S-001", "page": 1, "image": "page1.jpg",
     "sha256": "ACTUAL_PAGE_1_SHA256", "source_locator": "Archive/reference/image1"},
    {"source_id": "S-001", "page": 2, "image": "page2.jpg",
     "sha256": "ACTUAL_PAGE_2_SHA256", "source_locator": "Archive/reference/image2"}
  ],
  "targets": [{
    "region_id": "P01-R01", "page": 1,
    "bbox_original": [100, 200, 250, 230],
    "line_bbox_original": [0, 190, 1000, 290],
    "context_bbox_original": [0, 0, 1000, 1400],
    "anchor_bbox_original": [40, 200, 95, 230],
    "same_hand_samples": [
      {"sample_id": "E1", "source_id": "S-001", "page": 2,
       "bbox_original": [100, 200, 250, 230]}
    ]
  }],
  "verified_context": {"language": "Portuguese", "period": "19th century",
    "genre": "parish register", "clues": []}
}
```

Bounds are `[left, top, right, bottom]` in original pixels, with exclusive right/bottom edges. The target must fit inside its line and context. The preceding-word anchor must fit inside the line and precede the target, and it must sit on word boundaries: the build fails when ink runs across its left or right edge, because the box then starts or ends inside a word. At line start, omit it and set `target_at_line_start: true`. These anchor rules currently assume left-to-right text; adapt the helper for another writing direction rather than inventing a left-hand anchor.

The builder copies each page, verifies the frozen bytes against the pinned hash, then derives canonical PNG crops. Optional `target_image`, `line_image`, `context_image`, `anchor_image` and sample `image` paths must match source pixels exactly after RGBA decoding. Same-size shifted crops and JPEG recompression fail; omit optional paths to derive directly from the registered page. Full source bytes remain in coordinator `sources/`; canonical crops live in `crops/`. Worker crops are derived PNGs, not original JPEG file bytes.

A sample identity is **source ID + physical page + sample ID + exact bounds**. Equal coordinates on different pages do not collide. One sample ID on a given page cannot have conflicting bounds. Empty sample lists are allowed; B may abstain without secure same-hand evidence. Build then adds a warning such as "B will abstain on P01-R01", so you can add samples before preflight instead of finding the gap after the run.

Only D receives `verified_context`. Clues require `id`, `fact`, `provenance`, `independent_of_target: true` and `clue_certainty` (`certain`, `probable` or `uncertain`); verify that independence. A clue taken from an earlier reading that still carries `[?]` is `uncertain` at best. D receives the certainty with the clue. Modern place lists are contextual aids, not historical proof. Keep filenames neutral and exclude expected readings.

## Generated views

```sh
python scripts/method_packets.py build source/spec.json --out work/round-1
```

Build creates a frozen coordinator manifest, source snapshots, draft task folders and `preflight-template.json`. **Drafts are not ready to run.** Assets/views retain source/page identity, hashes, bounds, dimensions and transformations.

By default build prints a short summary: output folder, manifest and preflight template paths, packet ID, packet digest, counts and `warnings`. Add `--verbose` to print the full manifest. The manifest file is always complete, and its `warnings` list matches the summary.

- A receives neutral target crops and nearest-neighbour enlargements, up to 8×.
- B also receives neutral line/anchor views, a marked line locator and same-hand samples. Coloured locator boxes are orientation only, excluded from letter evidence.
- C receives complete lines, ordered enlarged tiles and target details.
- D receives page context plus line/target details, reusing a shared page once within its folder.

Balanced tiles retain overlap without a nearly duplicate final tile. Enlarged tiles overlap by at least one enlarged text line, estimated as the crop height up to 200 source pixels (at least 160 and at most 800 display pixels), so a tile edge does not cut the only copy of a line. Each tile's transform records `tile_overlap`. Near-identical same-page sample crops merge when overlap covers at least 85% of the smaller crop and the union is at most 125% of the larger area. Each alias retains exact source/page/sample/bounds; target references identify applicable aliases. Different pages never merge. A merged asset is not one word or an independent witness.

Tight boxes can cut descenders or ascenders. Set `"display": {"margin": 0.25}` to pad every target and line box by that fraction of its own height, taken from the pinned page and clamped to its edges. Default 0, maximum 1. The padded box becomes the asset's `bbox_original`, and each view's transform records `margin` with the fraction, pixels, requested and padded boxes and whether the page edge clamped it. Target identities, review regions and B's `target_location` keep the requested box. Inspect the padded views in preflight like any other.

No contrast variants are emitted; `display.contrast: true` is rejected. Do not sharpen or denoise worker images: JPEG blocks can become false strokes. Neutral enlargements add display size, not detail. Transparent display views use a logged white background; page reduction is for orientation only. Workers may create logged neutral derivatives in their private `work/`.

## Record the visual check and release inputs

Copy `preflight-template.json` to a review file outside the frozen inputs. For **every** target, actually open every `required_files` entry: frozen page, A's original/enlarged target views and B's marked line locator. Inspect additional line/sample views as needed. Check the right page, complete intended phrase, preceding anchor (or line start) and usable detail. Correct coordinates can still surround the wrong word.

Fill the review without changing `packet_digest`:

- `reviewed_by`: operator/context identity; `reviewed_at`: ISO timestamp including timezone.
- `inspected_files`: exact packet-relative paths actually opened, including all required files.
- `source_page_correct`, `target_complete`, `anchor_correct`, `views_usable`: actual boolean findings.
- For a target built with `target_at_line_start: true` there is no preceding word. Its template region has `line_start_correct` instead: record whether the target really starts its line, and leave `anchor_correct` as `null`. Any other value there fails. Anchored targets still need a boolean `anchor_correct` and have no `line_start_correct`.
- `source_quality`: `adequate_for_attempt` or `needs_better_source`. The template shows both as `adequate_for_attempt | needs_better_source`; replace it with one.
- `notes`: concrete observations, defects and source limitations.

Never fill passes from decoding success. `adequate_for_attempt` means useful evidence exists to inspect, not that the word is legible or certain.

```sh
python scripts/method_packets.py record-preflight work/round-1/coordinator-manifest.json work/review-round-1.json
python scripts/method_packets.py dispatch work/round-1/coordinator-manifest.json
```

`record-preflight` requires complete checks bound to unchanged inputs. It appends the review to `preflight-log.jsonl`, a hash-chained log that build starts, with the reviewer, the operating-system user and host, and the hash of every inspected file, then writes `preflight.json`. Recording again replaces the current review but keeps the old one: the log retains every review, and an existing `preflight.json` moves to `preflight-replaced/`. Failed checks or `needs_better_source` save a blocked result. `dispatch` uses the latest logged review and re-evaluates its checks and hashes; a `preflight.json` edited or written by hand, an edited or deleted log, or an inspected file changed since the review blocks release. Each task receipt names the review digest and how many reviews it replaced. It releases only frozen task inputs, excluding stray reports/private work, and adds each task's receipt. Returned paths under `dispatch/` are ready to give to the host; no model is called. Missing review, stale inputs or failed checks stop release.

If blocked, repair the crop/view or acquire a better source, then build in a **fresh** directory. Preserve earlier packets and receipts. Stop reader rounds when source pixels are the limit. Record actual context IDs and reports separately without editing the frozen manifest.

This enforces the helper's release workflow. It cannot prove that images were inspected, that intended words were selected, or that external agents cannot bypass it. Workers require a matching `dispatch-receipt.json` and return blocked if absent. Folder isolation remains procedural unless the host enforces it.

## Run and reconcile

Give each fresh context only its released prompt/task folder; the same model is allowed. Keep reports immutable outside inputs, linked to packet ID and actual host context IDs.

```sh
python scripts/method_packets.py summarize work/round-1/coordinator-manifest.json reports/A.json reports/B.json reports/C.json reports/D.json
```

Schema 1.2 reports include `packet_id` and source/page/asset/view identities. B's literal candidate requires `method_product.target_location` matching the target, with `preceding_anchor` (uncertain reading or line-start statement). Inspect the anchor and correspondences; matching coordinates alone do not establish a reading. C retains raw line output and character self-audit. The summarizer queues C candidates for coordinator comparison against A/B and pixels; it never clears letter conflicts. Abstentions are missing evidence, not agreement.

If any report is not `context_isolation: fresh`, lacks a context ID or reuses another method's context ID, `summarize` stops with an error (exit code 2) instead of a summary: the panel is invalid, so use the blind plus context double reading. Summaries retain `confidence: not_computed`. Metadata cannot authenticate method execution, contextual truth or transcription accuracy. Preserve later rounds separately; reruns and alternatives never add votes.

## Migration

Build/dispatch require **packet schema 1.2**: add pinned full pages and a preceding-word anchor (or explicit line start); remove contrast options and use recorded preflight/release. Omit crop paths if rescaled/recompressed. Replace legacy `same_hand_images` with page-qualified `same_hand_samples`. Historical schema 1.0/1.1 reports remain summarizable, but old packets must be rebuilt for the dispatch gate. Packet and case schemas are separate; no case or SQLite migration occurs.
