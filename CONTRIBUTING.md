# Contributing

Thanks for helping with the genealogy skills. This file covers setup, the checks to run before a pull request, and the one rule about data.

## Data rule

Never commit family data or real case data. That includes names, dates, places, record references, images and transcriptions from your own research or anyone else's. Tests, fixtures and examples use made-up people and sources only, such as the synthetic cases in `examples/` and `tests/fixtures/`. If you found a problem while working on real research, describe it with invented details.

## Setup

You need Python 3.10 or newer and Git. The helpers use only the standard library; the tests also need Pillow.

```sh
git clone https://github.com/rfsbraz/genealogy-agent-skills.git
cd genealogy-agent-skills
python -m pip install pillow
```

To try the skills in an agent, follow [INSTALL.md](INSTALL.md).

## Checks

These are the commands the CI job runs. The exact list of test files is in [.github/workflows/ci.yml](.github/workflows/ci.yml).

```sh
python validate_package.py
python scripts/build_manifest.py --check
for test in tests/check_*.py; do python "$test" || exit 1; done
python tests/test_repo.py
```

The loop runs the helper tests and the reading panel tests (`tests/check_panel_*.py`). CI also checks the installer:

```sh
python install.py --dest /tmp/genealogy-skills
python install.py --dest /tmp/genealogy-skills --apply
```

## Single-skill bundles

Some hosts, such as claude.ai, install each skill on its own, without the sibling folders. Skills under `skills/` link to the shared files in `genealogy-mode` (for example `../genealogy-mode/references/shared-contract.md`), and those files are kept in one place only. To get folders that work on their own, build them:

```sh
python scripts/package_skills.py
```

This writes one folder per skill to `dist/skills/<name>/`. Each one carries a copy of the files it links to from other skills under `shared/<skill>/`, with the links rewritten. The build also drops frontmatter keys that the Agent Skills spec does not allow, such as `disable-model-invocation`, because claude.ai rejects an upload that has them. Keep that key in `skills/`: Claude Code and Cursor use it to stop specialist skills loading on their own. `tests/check_bundles.py` checks that every relative link in every bundle resolves inside that bundle and that bundles carry only spec keys. Edit the files under `skills/`, never the copies in `dist/`, which is not committed.

`python scripts/package_skills.py --release` also writes the release assets to `dist/release/`: one claude.ai zip per skill, `genealogy-skills-claude-ai.zip` with all of them, `genealogy-plugin.zip` with the plugin, and `SHA256SUMS`. It checks the zips before writing the checksums. The Release workflow runs the same command when release-please creates a release and uploads the files to it with `gh release upload`. `tests/check_release_assets.py` covers the assets.

If you add, remove or change a file under `skills/`, `evaluation/` or `tests/`, or change `install.py`, `validate_package.py` or `genealogy.py`, regenerate the manifest and commit it:

```sh
python scripts/build_manifest.py
```

Do not edit version numbers or `CHANGELOG.md`. Releases are made by release-please from the commit messages.

## Skill descriptions

Each `description` in a `SKILL.md` frontmatter starts with "Use when", is written in the third person, names a near miss with "Not for", and stays within 200 characters, the claude.ai limit. Specialist skills start with "Use when genealogy-mode or the user", so they do not take requests from `genealogy-mode` on hosts that let every skill load on its own. `tests/check_skill_routing.py` checks these rules.

## Privacy check

CI also runs `python scripts/privacy_scan.py`. It looks for email addresses, phone numbers and home folder paths, plus extra terms from a repository secret. GitHub does not pass secrets to pull requests from forks, so a pull request from a fork only gets the built-in checks. Run `python scripts/privacy_scan.py` locally to get the same built-in result. The full scan runs again on `main` after merging.

## Reference files

A reference file over 100 lines starts with a `Contents:` line under its title that links every `##` section, because an agent may only preview the top of a long file. Every reference an agent can reach from a `SKILL.md` must be linked from that `SKILL.md` directly, even when another reference also links it, so nothing sits more than one link away. `tests/check_references.py` checks both.

## Pull requests

- Open an issue first for anything larger than a small fix, so we can agree on the approach.
- Keep each pull request to one change, with tests for code changes.
- Use a [Conventional Commits](https://www.conventionalcommits.org/) title with a scope, for example `fix(queue): ...` or `docs(reading): ...`. `feat` and `fix` appear in the release notes; `docs`, `test` and `chore` do not.
- Fill in the pull request template, including the AI use section.

By contributing you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems as described in [SECURITY.md](SECURITY.md), not in a public issue.
