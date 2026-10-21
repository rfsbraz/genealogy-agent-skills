#!/usr/bin/env python3
"""Install the plugin the way users do, with each host's own CLI, and check what the host sees.

Usage: python scripts/smoke_install.py HOST --tools DIR [--cli PATH]
HOST is claude, gemini, codex or skills. Without --cli the pinned CLI is installed with npm
under DIR/HOST. Every run uses a fresh HOME, so it never touches your own host settings, and
none of the steps sign in or call a model.

Checks, per host:
- the plugin installs from this checkout and is listed as enabled, at the release version;
- the host sees every skill (and, for Claude Code, the commands);
- every relative Markdown link in the installed copy resolves.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'genealogy'
MARKETPLACE = 'genealogy-agent-skills'


def _claude_version() -> str:
    script = (ROOT / 'scripts' / 'install_host_validators.sh').read_text(encoding='utf-8')
    return re.search(r'^CLAUDE_CODE_VERSION=(\S+)$', script, re.M).group(1)


HOSTS = {
    'claude': {'package': '@anthropic-ai/claude-code', 'version': _claude_version(), 'bin': 'claude'},
    'gemini': {'package': '@google/gemini-cli', 'version': '0.65.0', 'bin': 'gemini'},
    'codex': {'package': '@openai/codex', 'version': '0.163.0', 'bin': 'codex'},
    'skills': {'package': 'skills', 'version': '1.7.4', 'bin': 'skills'},
}


def expected_skills() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md'))


def expected_commands() -> list[str]:
    return sorted(p.stem for p in (ROOT / 'commands').glob('*.md'))


def expected_version() -> str:
    return json.loads((ROOT / '.release-please-manifest.json').read_text(encoding='utf-8'))['.']


def compare(label: str, found, expected) -> list[str]:
    found, expected = set(found), set(expected)
    if found == expected:
        return []
    parts = []
    if expected - found:
        parts.append('missing ' + ', '.join(sorted(expected - found)))
    if found - expected:
        parts.append('unexpected ' + ', '.join(sorted(found - expected)))
    return [f'{label}: ' + '; '.join(parts)]


LINK = re.compile(r'\]\(([^)\s]+)\)')


def broken_links(root: Path) -> list[str]:
    broken = []
    for md in sorted(Path(root).rglob('*.md')):
        for target in LINK.findall(md.read_text(encoding='utf-8', errors='replace')):
            if re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I) or target.startswith('#'):
                continue
            path = target.split('#', 1)[0]
            if path and not (md.parent / path).exists():
                broken.append(f'{md.relative_to(root)} -> {target}')
    return broken


def check_skill_tree(root: Path, skills: list[str]) -> list[str]:
    root = Path(root)
    found = [p.parent.name for p in root.glob('*/SKILL.md')]
    errors = compare(f'skills in {root}', found, skills)
    for link in broken_links(root):
        errors.append(f'broken link: {link}')
    return errors


def parse_claude_details(text: str) -> list[str]:
    match = re.search(r'^\s*Skills \((\d+)\)\s+(.*)$', text, re.M)
    if not match:
        return []
    return [name.strip() for name in match.group(2).split(',') if name.strip()]


def parse_gemini_list(text: str):
    head = re.search(r'^\S+\s+' + PLUGIN + r' \(([^)]+)\)\s*$', text, re.M)
    if not head:
        return None
    body = text[head.end():]
    nxt = re.search(r'^\S', body, re.M)
    if nxt:
        body = body[:nxt.start()]
    path = re.search(r'^\s*Path:\s*(.+)$', body, re.M)
    skills_block = body.split('Agent skills:', 1)[1] if 'Agent skills:' in body else ''
    skills = re.findall(r'^\s{2,}([a-z0-9][a-z0-9-]*):\s', skills_block, re.M)
    return {
        'version': head.group(1),
        'path': path.group(1).strip() if path else None,
        'enabled': bool(re.search(r'Enabled \(User\):\s*true', body)),
        'skills': skills,
    }


class Runner:
    def __init__(self, cli: str, home: Path):
        self.cli = cli
        self.env = dict(os.environ, HOME=str(home), DISABLE_TELEMETRY='1', DO_NOT_TRACK='1',
                        GEMINI_CLI_DISABLE_TELEMETRY='1', NO_COLOR='1', CI='1')
        for key in list(self.env):
            if key.endswith('_API_KEY'):
                del self.env[key]
        self.log: list[str] = []

    def __call__(self, *args, stdin: str | None = None, cwd: Path = ROOT) -> str:
        cmd = [self.cli, *args]
        proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True, env=self.env,
                              cwd=cwd, timeout=300)
        out = proc.stdout + proc.stderr
        self.log.append('$ ' + ' '.join([Path(self.cli).name, *args]) + '\n' + out)
        if proc.returncode != 0:
            raise SystemExit(f'{" ".join(cmd)} exited {proc.returncode}:\n{out}')
        return out


def smoke_claude(run: Runner, home: Path) -> list[str]:
    run('plugin', 'marketplace', 'add', str(ROOT))
    run('plugin', 'install', f'{PLUGIN}@{MARKETPLACE}')
    listed = _json_tail(run('plugin', 'list', '--json'))
    entry = next((p for p in listed if p.get('id') == f'{PLUGIN}@{MARKETPLACE}'), None)
    if not entry:
        return [f'claude plugin list does not show {PLUGIN}@{MARKETPLACE}']
    errors = []
    if not entry.get('enabled'):
        errors.append('claude: plugin is not enabled')
    if entry.get('version') != expected_version():
        errors.append(f"claude: version {entry.get('version')}, expected {expected_version()}")
    details = parse_claude_details(run('plugin', 'details', PLUGIN))
    errors += compare('claude skills and commands', details, expected_skills() + expected_commands())
    errors += check_skill_tree(Path(entry['installPath']) / 'skills', expected_skills())
    return errors


def smoke_gemini(run: Runner, home: Path) -> list[str]:
    # The folder trust prompt has no flag, so answer it on stdin.
    run('extensions', 'install', str(ROOT), '--consent', stdin='y\n')
    parsed = parse_gemini_list(run('extensions', 'list'))
    if not parsed:
        return [f'gemini extensions list does not show {PLUGIN}']
    errors = []
    if not parsed['enabled']:
        errors.append('gemini: extension is not enabled')
    if parsed['version'] != expected_version():
        errors.append(f"gemini: version {parsed['version']}, expected {expected_version()}")
    errors += compare('gemini skills', parsed['skills'], expected_skills())
    errors += check_skill_tree(Path(parsed['path']) / 'skills', expected_skills())
    return errors


def smoke_codex(run: Runner, home: Path) -> list[str]:
    run('plugin', 'marketplace', 'add', str(ROOT))
    added = run('plugin', 'add', f'{PLUGIN}@{MARKETPLACE}')
    listed = _json_tail(run('plugin', 'list', '--json'))
    entry = next((p for p in listed.get('installed', []) if p.get('pluginId') == f'{PLUGIN}@{MARKETPLACE}'), None)
    if not entry:
        return [f'codex plugin list does not show {PLUGIN}@{MARKETPLACE}']
    errors = []
    if not (entry.get('installed') and entry.get('enabled')):
        errors.append('codex: plugin is not installed and enabled')
    if entry.get('version') != expected_version():
        errors.append(f"codex: version {entry.get('version')}, expected {expected_version()}")
    root = re.search(r'^Installed plugin root:\s*(.+)$', added, re.M)
    if not root:
        return errors + ['codex: plugin add did not report the installed plugin root']
    errors += check_skill_tree(Path(root.group(1).strip()) / 'skills', expected_skills())
    return errors


def smoke_skills(run: Runner, home: Path) -> list[str]:
    errors = []
    listed = run('add', str(ROOT), '--list')
    found = re.search(r'Found (\d+) skills', listed)
    if not found or int(found.group(1)) != len(expected_skills()):
        errors.append(f"skills --list: found {found.group(1) if found else 'none'}, expected {len(expected_skills())}")
    project = home / 'project'
    project.mkdir()
    run('add', str(ROOT), '--skill', '*', '-a', 'claude-code', '-y', cwd=project)
    errors += check_skill_tree(project / '.claude' / 'skills', expected_skills())
    return errors


def _json_tail(text: str):
    """Parse the JSON document in a CLI's output, skipping any warning lines before it."""
    start = min(i for i in (text.find('['), text.find('{')) if i >= 0)
    return json.JSONDecoder().raw_decode(text[start:])[0]


SMOKES = {'claude': smoke_claude, 'gemini': smoke_gemini, 'codex': smoke_codex, 'skills': smoke_skills}


def install_cli(host: str, tools: Path) -> str:
    pin = HOSTS[host]
    prefix = tools / host
    subprocess.run(['npm', 'install', '--silent', '--no-fund', '--no-audit', '--prefix', str(prefix),
                    f"{pin['package']}@{pin['version']}"], check=True)
    return str(prefix / 'node_modules' / '.bin' / pin['bin'])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('host', choices=sorted(HOSTS))
    parser.add_argument('--tools', type=Path, help='where to install the pinned CLI')
    parser.add_argument('--cli', help='use this CLI instead of installing the pinned one')
    parser.add_argument('--log', type=Path, help='write every command and its output here')
    args = parser.parse_args(argv)
    if not args.cli and not args.tools:
        parser.error('give --tools or --cli')
    cli = args.cli or install_cli(args.host, args.tools)
    with tempfile.TemporaryDirectory(prefix=f'smoke-{args.host}-') as tmp:
        home = Path(tmp)
        run = Runner(cli, home)
        try:
            errors = SMOKES[args.host](run, home)
        finally:
            if args.log:
                args.log.write_text('\n'.join(run.log), encoding='utf-8')
    summary = {'host': args.host, 'cli_version_pin': HOSTS[args.host]['version'],
               'expected_version': expected_version(), 'skills': len(expected_skills()), 'errors': errors}
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
