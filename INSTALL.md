# Install the genealogy skills

These steps are written for an AI agent to follow on behalf of a user. Each step has a check. Steps marked **(human)** need the user to click or type something; ask them to do it and wait for their answer.

Repository: https://github.com/rfsbraz/genealogy-agent-skills
Plugin name: `genealogy`. The entry point skill is `genealogy-mode`.

## 1. Find out which host you are running in

| If this is true | Host | Go to |
|---|---|---|
| You are Grok Bot | Grok Bot | [Grok Bot](#grok-bot) |
| You are the agent inside the Cursor editor or Cursor CLI | Cursor | [Cursor](#cursor) |
| You are Claude Code and `claude --version` works in your shell | Claude Code | [Claude Code](#claude-code) |
| You are Codex (CLI, IDE extension or ChatGPT desktop) and `codex --version` works | Codex | [Codex](#codex) |
| `gemini --version` works and the user uses Gemini CLI | Gemini CLI | [Gemini CLI](#gemini-cli) |
| `agy` is installed and the user uses Antigravity CLI | Antigravity CLI | [Antigravity CLI](#antigravity-cli) |
| You are Claude in the claude.ai web or desktop chat, with no shell on the user's computer | Claude.ai | [Claude.ai](#claudeai) |
| None of the above, but you can run Python 3.10+ and write to your skills folder | Other | [Any other agent](#any-other-agent) |

If more than one row fits, or none does, ask the user which app they want the skills in.

## 2. Install and verify

### Claude Code

Run in a shell:

```
claude plugin marketplace add rfsbraz/genealogy-agent-skills
claude plugin install genealogy@genealogy-agent-skills
```

Expected: `Successfully added marketplace: genealogy-agent-skills` and `Successfully installed plugin: genealogy@genealogy-agent-skills (scope: user)`.

Check:

```
claude plugin details genealogy
```

The `Component inventory` section must list the skills, including `genealogy-mode`, and the `tree` and `story` commands. The plugin loads in the next session, or after `/reload-plugins` in an open one. In a session the skill shows as `/genealogy:genealogy-mode`, and the commands as `/genealogy:tree` and `/genealogy:story`.

### Codex

Run in a shell:

```
codex plugin marketplace add rfsbraz/genealogy-agent-skills
codex plugin add genealogy@genealogy-agent-skills
```

Check:

```
codex plugin list
```

The row `genealogy@genealogy-agent-skills` must say `installed, enabled`. Restart Codex, then run `/skills` or type `$genealogy-mode` to confirm it is there. In the ChatGPT desktop app you can also install "Genealogy" from the Plugins Directory after adding the marketplace **(human)**.

If this Codex has no `plugin` command, install the skills as plain user skills instead:

```
git clone https://github.com/rfsbraz/genealogy-agent-skills
python genealogy-agent-skills/install.py --dest ~/.agents/skills --apply
```

Check that `~/.agents/skills/genealogy-mode/SKILL.md` exists, then restart Codex.

### Gemini CLI

Run in a shell, not as a slash command inside an interactive Gemini session:

```
gemini extensions install https://github.com/rfsbraz/genealogy-agent-skills
```

Gemini asks the user to confirm the install **(human)**. Only add `--consent` to skip that question if the user has told you to install without asking.

Check:

```
gemini extensions list
gemini skills list
```

The first must show `genealogy (2.0.0)`. The second must show `genealogy-mode [Enabled]`. Restart Gemini CLI so the session picks up the extension. In a session, `/tree` and `/story` are available (shown as `/genealogy.tree` and `/genealogy.story` if another extension already uses those names). <!-- x-release-please-version -->

Only `genealogy-mode`, `genealogy-interview` and `genealogy-narrative` are meant to load on their own; the other skills wait for the user or `genealogy-mode`. Claude Code, Cursor and Codex enforce this. Gemini CLI cannot enforce it, so a specialist skill may still load on its own there.

### Antigravity CLI

If the extension is already installed in Gemini CLI on this computer, convert it:

```
agy plugin import gemini
```

Otherwise install the skills into the Antigravity skills folder:

```
git clone https://github.com/rfsbraz/genealogy-agent-skills
python genealogy-agent-skills/install.py --dest ~/.gemini/antigravity-cli/skills
python genealogy-agent-skills/install.py --dest ~/.gemini/antigravity-cli/skills --apply
```

The first `install.py` run is a preview that lists one `install` action per skill, including `genealogy-mode`. For one workspace only, use `--dest .agents/skills` instead. Check that `genealogy-mode/SKILL.md` exists in the folder you chose, then start a new `agy` session.

### Cursor

Once Genealogy is listed in the Cursor Marketplace: open Customize, find Genealogy, select Install and choose a scope **(human)**.

Until then, load it as a local plugin. Clone it straight into the local plugins folder (Cursor skips symlinks that point outside that folder):

```
git clone https://github.com/rfsbraz/genealogy-agent-skills ~/.cursor/plugins/local/genealogy
```

Check that `~/.cursor/plugins/local/genealogy/.cursor-plugin/plugin.json` exists. Then ask the user to restart Cursor or run Developer: Reload Window, open Customize and confirm the Genealogy skills are listed **(human)**. Typing `/tree` or `/story` in the agent chat should offer the plugin's commands. On Teams and Enterprise plans an admin may have turned local plugins off.

### Grok Bot

If Genealogy appears in Connect apps: ask the user to open Connect apps, search "Genealogy" and add it **(human)**. Check that the skills appear when the user types `/` in the composer.

If it is not listed yet, use the skills from a clone on your own computer:

```
git clone https://github.com/rfsbraz/genealogy-agent-skills ~/genealogy-agent-skills
ls ~/genealogy-agent-skills/skills
```

Check that the list includes `genealogy-mode`, and that `~/genealogy-agent-skills/skills/genealogy-mode/SKILL.md` starts with `name: genealogy-mode`. Then save a private skill called "Genealogy" whose instructions say: for any genealogy or family-history task, read `~/genealogy-agent-skills/skills/genealogy-mode/SKILL.md` and follow it, loading the other skills in that folder as it directs.

### Claude.ai

You cannot install skills into claude.ai yourself. Give the user these steps **(human)**:

1. On Free, Pro or Max: Settings > Capabilities, turn on Code execution and file creation. On Team or Enterprise an owner enables Skills and code execution.
2. Download `genealogy-skills-claude-ai.zip` from the latest release at https://github.com/rfsbraz/genealogy-agent-skills/releases and unzip it. It holds one zip per skill. If the release has no such file, zip each folder under `skills/` on its own, with the skill folder at the top of the zip. Before zipping, delete the `disable-model-invocation: true` line from each `SKILL.md` that has it; claude.ai rejects uploads with that line. On claude.ai the specialist skills can then load on their own.
3. Go to Customize > Skills, click +, then + Create skill, then Upload a skill. Upload `genealogy-mode` first, then the others.

Check: each uploaded skill is listed in Customize > Skills and switched on.

### Any other agent

```
git clone https://github.com/rfsbraz/genealogy-agent-skills
python genealogy-agent-skills/install.py --dest <skills folder>
python genealogy-agent-skills/install.py --dest <skills folder> --apply
```

The first run only previews and must list one `install` action per skill, including `genealogy-mode`. The installer never overwrites a skill that differs from this one; it stops and makes no changes. Check that `<skills folder>/genealogy-mode/SKILL.md` exists.

## 3. Tell the user how to start

When the check passes, tell the user:

> The genealogy skills are installed. To begin, say "start a genealogy case" and tell me who or what you want to research. If you do not have a tree yet, say "Interview me to start my family tree" and I will ask one question at a time. Once someone is in the case, you can ask for their life as a story.

### Interview and story modes

| User says | Skill | What happens |
|---|---|---|
| "Interview me to start my family tree", `/tree start` | `genealogy-interview` | One question at a time, building a provisional seed tree. `/tree add`, `review`, `correct`, `pause`, `resume` and `research` continue it. |
| "Tell Ana's life as a story", `/story PERSON` | `genealogy-narrative` | A story from the person's current evidence, in `--style documentary`, `evocative` (default) or `novelized`, with provenance notes. |

The user can switch between interview, research and story at any time; the interview is saved before switching. Commands by host: `/genealogy:tree` and `/genealogy:story` in Claude Code, `/tree` and `/story` in Cursor and Gemini CLI. In Codex and other hosts, the user can type `/tree start` or `/story PERSON` as a normal message and genealogy-mode routes it. See `docs/workflows/modes.md`.

"Start a genealogy case" and other research requests go to `genealogy-mode`, which plans the case and calls the other skills. If your host picks a different skill, invoke genealogy-mode by name: `/genealogy:genealogy-mode` in Claude Code, `$genealogy-mode` in Codex. The other skills load only when genealogy-mode routes to them or the user names them, for example `/genealogy:genealogy-reporting` or `$genealogy-reporting`.

## Sources

Commands above were checked against:

- Claude Code: https://code.claude.com/docs/en/discover-plugins and https://code.claude.com/docs/en/plugin-marketplaces
- Codex: https://developers.openai.com/codex/plugins/build and https://developers.openai.com/codex/skills; `codex plugin add` from the Codex CLI help
- Gemini CLI: https://geminicli.com/docs/extensions/reference/ and https://geminicli.com/docs/cli/custom-commands/
- Antigravity CLI: https://antigravity.google/docs/cli/gcli-migration/
- Cursor: https://cursor.com/docs/plugins
- Grok Bot: https://docs.x.ai/grok-bot/skills-routines-and-automations
- Claude.ai: https://support.claude.com/en/articles/12512180-use-skills-in-claude
