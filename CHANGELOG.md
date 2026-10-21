# Changelog

## [2.1.0](https://github.com/rfsbraz/genealogy-agent-skills/compare/v2.0.1...v2.1.0) (2026-10-21)


### Features

* **antigravity:** add a native Antigravity plugin manifest ([#37](https://github.com/rfsbraz/genealogy-agent-skills/issues/37)) ([6bfceef](https://github.com/rfsbraz/genealogy-agent-skills/commit/6bfceef7759efaffa7878d37ab3edb32ac818dda)), closes [#36](https://github.com/rfsbraz/genealogy-agent-skills/issues/36)
* **gedcom:** check GEDCOM files and import them as provisional cases ([#44](https://github.com/rfsbraz/genealogy-agent-skills/issues/44)) ([294bf75](https://github.com/rfsbraz/genealogy-agent-skills/commit/294bf75a1649993c62938dd2021317d81b9f7c0c)), closes [#43](https://github.com/rfsbraz/genealogy-agent-skills/issues/43)
* **gedcom:** export reviewed conclusions with their sources and a loss report ([#46](https://github.com/rfsbraz/genealogy-agent-skills/issues/46)) ([88826da](https://github.com/rfsbraz/genealogy-agent-skills/commit/88826daf8204d054aaba6862f10b13f4b53cddf0)), closes [#45](https://github.com/rfsbraz/genealogy-agent-skills/issues/45)
* **planner:** find tree gaps from a per-country source registry ([#48](https://github.com/rfsbraz/genealogy-agent-skills/issues/48)) ([f21247e](https://github.com/rfsbraz/genealogy-agent-skills/commit/f21247e750332968e5af81ff476461b1c0fbfc59)), closes [#11](https://github.com/rfsbraz/genealogy-agent-skills/issues/11)
* **skills:** add license, compatibility and a release-stamped metadata.version ([#35](https://github.com/rfsbraz/genealogy-agent-skills/issues/35)) ([a32e5c5](https://github.com/rfsbraz/genealogy-agent-skills/commit/a32e5c513b2cfc607b701c3405a923327e2235eb))

## [2.0.1](https://github.com/rfsbraz/genealogy-agent-skills/compare/v2.0.0...v2.0.1) (2026-10-21)


### Bug Fixes

* **packaging:** build self-contained single-skill bundles ([#24](https://github.com/rfsbraz/genealogy-agent-skills/issues/24)) ([5165cb4](https://github.com/rfsbraz/genealogy-agent-skills/commit/5165cb41100210fa2e4ffa1547caf047d1e48cc9)), closes [#23](https://github.com/rfsbraz/genealogy-agent-skills/issues/23)
* **reading-method:** add not_blind method_id for a non-blind double reading ([#17](https://github.com/rfsbraz/genealogy-agent-skills/issues/17)) ([62963e8](https://github.com/rfsbraz/genealogy-agent-skills/commit/62963e8173b7adde5c43446222f947a2b3471636)), closes [#12](https://github.com/rfsbraz/genealogy-agent-skills/issues/12)
* **release:** attach claude.ai and plugin zips to each release ([#28](https://github.com/rfsbraz/genealogy-agent-skills/issues/28)) ([b1d6d16](https://github.com/rfsbraz/genealogy-agent-skills/commit/b1d6d166eb5bd62ba979007b51085e0e985de0e2)), closes [#27](https://github.com/rfsbraz/genealogy-agent-skills/issues/27)
* **skills:** pass claude.ai frontmatter checks and shorten descriptions ([#26](https://github.com/rfsbraz/genealogy-agent-skills/issues/26)) ([20ad65e](https://github.com/rfsbraz/genealogy-agent-skills/commit/20ad65efc37a69730af10b45f8fdeee3a9b94027)), closes [#25](https://github.com/rfsbraz/genealogy-agent-skills/issues/25)

## 2.0.0 (2026-10-18)


### ⚠ BREAKING CHANGES

* **skills:** the entry skill is now genealogy-mode (/genealogy:genealogy-mode in Claude Code, $genealogy-mode in Codex) and the manuscript reader is genealogy-read-manuscripts. Old invocation names stop working. Copy-based installs should remove the old genealogy-orchestrator and read-manuscripts folders after updating.

### Features

* **reading:** warn when B will abstain, add a view margin and shorten build output (#73) (f26bc16)
* **skills:** rename the entry and manuscript skills and load only entry skills on their own (#58) (37269dd)


### Bug Fixes

* **queue:** describe every CLI option and refuse inline JSON with a clear message (#75) (be84cf0)

## 1.4.3 (2026-10-18)


### Features

* **case:** add the host adapter contract for repositories that stay canonical (#71) (fd43f65)
* **case:** rereads that supersede earlier readings and generated fact files and tree notes (#22) (a8b6677)
* **proof:** scoped source-supported findings before full proof review (#21) (cf24912)
* **queue:** register a set of page images as one document version (#70) (46f2f8f)
* **queue:** restore from export, host-canonical mode and external-run rereads (#69) (e0a31f7)
* **reading:** bind method reports to their packet source, page and views (#39) (c1e5c32)
* **reading:** carry a structured reading_method block after the reading (#77) (8dec62e)
* **reading:** derive packet crops from pinned source pages (#52) (df2aef1)
* **reading:** four reading methods in separate contexts and complete quick entries (#20) (d83147c)
* **reading:** give the same-hand reader the target's place in its line (#54) (7cf6515)
* **reading:** port v1.4.2 display packets, page-qualified samples and line review (#38) (35f3082)
* **reading:** record and enforce the pre-run packet inspection (#55) (d47f7cf)


### Bug Fixes

* **reading:** deduplicate pages, samples and tiles in reading packets (#53) (c83156c)
* **reading:** fail cleanly on malformed packet input and reports (#37) (2ae07d8)
* **reading:** name valid preflight values, review line-start targets without an anchor and require clue certainty (#72) (5d5f8b2)
* **reading:** stop emitting contrast views in reading packets (#51) (0bc0f81)
* **reading:** stop the panel when separate contexts are unavailable (#30) (9a99e0d)
* **sources:** explain and check the place, period and record family filters (#74) (29e8e1b)


### Miscellaneous Chores

* release 1.4.3 (#59) (663185d)

## 1.3.0 (2026-10-17)

27 skills: 26 for everyday use plus the maintainer evaluation skill in `evaluation/`. Adds a conversational way to start a tree and a way to tell an ancestor's life as a story.

### Added

- `genealogy-interview`: start or extend a family tree by chatting. It asks one question at a time, uses everything the user already gave, and handles unknowns, multiple relationships, partial dates, corrections, pause and resume, and a direct handoff to research. Say "Interview me to start my family tree".
- An offline interview helper (`genealogy.py interview`) creates a seed case, applies attributed turns, saves testimony, citations and provisional conclusions, and keeps corrections. Expected revisions, local locks, atomic replacement and idempotent turn IDs protect saved state. The host agent runs the chat and reads the user's words.
- `genealogy-narrative`: documentary, evocative and novelized styles, with period detail where the sources support it. Passage-level notes separate records, recollection, inference, researched context and imagined scenes. The romantic style does not invent relationships or consequential events.
- A read-only story helper (`genealogy.py story`) for brief, check and render. Stories keep the evidence digest they were written from and stay outside the research graph, so fiction cannot become family-tree evidence.
- `/tree` and `/story` commands for Claude Code, Cursor and Gemini CLI that hand off to the two new skills. Other hosts accept the same text as a normal message.
- `docs/workflows/modes.md` shows how interview, investigation and story modes connect.

### Changed

- The GPS policy now explains the single-source distinction: a fact may have one immediate citation within broader documented research. The suite does not require two documents per field or judge evidence sufficiency by count. Reviewed conclusions still need all five GPS assessments, and a story is never genealogical proof.
- Case schema remains 1.1; no migration is needed.

### Limits

- The interview helper creates seed cases; it does not merge an existing tree. A stale story needs a real review before its fingerprint is updated. Local locks do not replace a distributed database.

### Tests

- 26 new interview and narrative checks: attribution, uncertainty, correction history, safe retry, stale revisions, failed writes, multiple relationship types, resume, source references, stale stories, and keeping fiction apart from evidence.
- Existing helper, document queue and GPS checks pass with counts updated to 27 skills (26 installed by default).

## 1.2.0 (2026-10-17)

Same skills as 1.1, with a simpler front door and stronger evidence review. 25 skills, 24 installed by default; the evaluation skill moved to `evaluation/`.

### Added

- One everyday entry point with three requests: research a person, read a document, or continue and check progress. Short progress cards, one blocking question at a time, useful links and text status labels. Full evidence stays available. See `docs/workflows/everyday.md`.
- An explicit GPS policy with a structured five-element review: full citation text, source, informant and information assessments, alternatives, conflicts and written reasoning. Case schema 1.1 blocks supported or rejected conclusions that have no current review record, and an evidence digest marks old reviews stale when the evidence changes.
- A country starter database: 14 profiles and 31 official entry points, with roles, native search terms, local discovery routes, evidence URLs, check dates and fallback steps. Countries outside the database go through open discovery.
- A small offline command interface: `genealogy.py start`, `sources`, `countries`, `status` and `check`. It does not run a model or make web requests.
- Usability guidance for evaluation: time to useful action, repeated intake, resumption and user comprehension, alongside evidence quality.

### Changed

- The quick and detailed reading skills and the document ledger are kept as they were.
- New cases use schema 1.1. Schema 1.0 cases stay readable and can be audited with `--gps` without rewriting evidence.
- The evidence digest is case-wide: an evidence, identity or conclusion change means reviews across the case need another look. Checkpoint, task and mail updates do not affect it.

### Limits

- Software checks that GPS assessments are present and consistent. It cannot certify historical truth, authenticate a reviewer or judge whether an argument is sound.
- No web application, archive adapters, mail client, model worker or always-on timer is included. Recovering interrupted jobs is left to the host.

### Tests

- 25 new GPS, country lookup and command interface tests. The country validator accepts all 14 profiles and 31 source entries, and the GPS schema matches the case schema.
- Official entry points were checked against primary sites. Live catalogue searches, account access, payments and mail were not exercised.
