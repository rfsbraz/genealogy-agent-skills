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

## Host validators

A separate CI job runs the validators the hosts use themselves, on the built release assets: `skills-ref validate` and Anthropic's `quick_validate.py` on every skill zip, and `claude plugin validate --strict --profile directory` on the repository, on `.claude-plugin/plugin.json` and on the plugin zip. The raw folders under `skills/` are not checked this way, because they keep `disable-model-invocation`, which both skill validators reject. To run them locally (needs Node.js 22 and curl; best inside a virtual environment):

```sh
scripts/install_host_validators.sh /tmp/validators
python scripts/package_skills.py --release
python scripts/run_host_validators.py dist/release \
  --quick-validate /tmp/validators/quick_validate.py \
  --claude /tmp/validators/npm/node_modules/.bin/claude
```

The tool versions are pinned in `scripts/install_host_validators.sh`. The Release workflow runs the same checks before it uploads the assets.

## Install smoke test

The Install smoke workflow installs the plugin from the checkout with each host's own CLI, the way users do: `claude plugin marketplace add` and `claude plugin install`, `gemini extensions install`, `codex plugin marketplace add` and `codex plugin add`, and `npx skills add`. It then checks that the host lists the plugin as enabled at the version in `.release-please-manifest.json`, that it sees every skill (and, for Claude Code, the `tree` and `story` commands), and that every relative link in the installed copy resolves. It runs on pull requests, on main and nightly, on GitHub-hosted runners. None of the steps sign in or call a model, so it needs no secrets. To run it locally (needs Node.js 22.20 or newer and npm):

```sh
python scripts/smoke_install.py claude --tools /tmp/smoke-tools
```

Use `gemini`, `codex` or `skills` for the other hosts, or `--cli PATH` to use a CLI you already have. Each run uses a throwaway `HOME`, so it leaves your own host settings alone. The CLI versions are pinned in `scripts/smoke_install.py`; Claude Code uses the pin from `scripts/install_host_validators.sh`. Antigravity is not covered yet.

## Optional frontmatter fields

Every `SKILL.md` sets `license: MIT` and `metadata.author`. Skills that need more than the agent itself say so in `compatibility` (at most 500 characters): the Python version and packages for skills with scripts, network access for the discovery skills, and a mail tool for archive correspondence. Do not add `metadata.version` to a `SKILL.md`. The packaging build adds it to each bundle from `.release-please-manifest.json`, the file release-please bumps, because a version inside `SKILL.md` would change files that `manifest.json` checksums on every release PR. `tests/check_spec_fields.py` checks these rules.

## Skill descriptions

Each `description` in a `SKILL.md` frontmatter starts with "Use when", is written in the third person, names a near miss with "Not for", and stays within 200 characters, the claude.ai limit. Specialist skills start with "Use when genealogy-mode or the user", so they do not take requests from `genealogy-mode` on hosts that let every skill load on its own. `tests/check_skill_routing.py` checks these rules.

## Plugin evals

`evals/` is a `claude plugin eval` suite: trigger cases and the benchmark cases. Running it calls a paid model, so CI only runs `python tests/check_evals.py`, which needs no account. If you change the benchmark, run `python scripts/build_evals.py` and commit the result. If you change a skill description, add or adjust a `trigger-*` case in `scripts/build_evals.py`. Commands and the cost estimate are in [docs/VALIDATION.md](docs/VALIDATION.md#plugin-evals).

## Privacy check

CI also runs `python scripts/privacy_scan.py`. It looks for email addresses, phone numbers and home folder paths, plus extra terms from a repository secret. GitHub does not pass secrets to pull requests from forks, so a pull request from a fork only gets the built-in checks. Run `python scripts/privacy_scan.py` locally to get the same built-in result. The full scan runs again on `main` after merging.

## Reference files

A reference file over 100 lines starts with a `Contents:` line under its title that links every `##` section, because an agent may only preview the top of a long file. Every reference an agent can reach from a `SKILL.md` must be linked from that `SKILL.md` directly, even when another reference also links it, so nothing sits more than one link away. `tests/check_references.py` checks both.

## Pull requests

- Open an issue first for anything larger than a small fix, so we can agree on the approach.
- Keep each pull request to one change, with tests for code changes.
- Use a [Conventional Commits](https://www.conventionalcommits.org/) title with a scope, for example `fix(queue): ...` or `docs(reading): ...`. `feat` and `fix` appear in the release notes; `docs`, `test` and `chore` do not.
- Fill in the pull request template, including the AI use section.

## Low-effort and automated PRs

genealogy-agent-skills is maintained in my spare time, and every PR takes real time to review. I'm happy to get contributions from people who use genealogy-agent-skills and want to make it better.

I will close, without review, PRs that look like contribution farming: accounts opening many PRs across unrelated projects, or changes made mainly to collect contributions rather than to fix something you ran into. This applies even when the change itself is correct.

AI-assisted PRs are fine if you've read and understood the change and can answer questions about it. Please say so in the PR.

The easiest way to get a PR merged is to start with an issue, agree on the approach there, and then open the PR.

By contributing you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems as described in [SECURITY.md](SECURITY.md), not in a public issue.
