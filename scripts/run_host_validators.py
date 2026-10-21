#!/usr/bin/env python3
"""Run the hosts' own validators on the built release assets.

- skills-ref validate (the Agent Skills reference validator) on every unpacked
  <skill>.zip
- Anthropic's quick_validate.py (what skill uploads to claude.ai check) on every
  unpacked <skill>.zip
- claude plugin validate --strict --profile directory on the repository (its
  marketplace.json), on .claude-plugin/plugin.json and on the unpacked
  genealogy-plugin.zip

The raw folders under skills/ are not validated here: they keep
disable-model-invocation for Claude Code and Cursor, which both skill
validators reject. Build the assets first with
python scripts/package_skills.py --release, and install the pinned tools with
scripts/install_host_validators.sh.

Prints a JSON summary and exits 1 if any check fails. Add a check by adding a
function to CHECKS.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ZIP = 'genealogy-plugin.zip'
COMBINED_ZIP = 'genealogy-skills-claude-ai.zip'


def run(command, label, log):
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    log.append(f'$ {" ".join(command)}\n{output}\nexit {result.returncode}')
    return result.returncode == 0 and 'Skill is valid!' in output if label == 'quick_validate' else result.returncode == 0


def per_skill(label, command):
    def check(work, args, log):
        passed, failed = 0, []
        for folder in sorted((work / 'skills').iterdir()):
            if run(command(args, folder), label, log):
                passed += 1
            else:
                failed.append(folder.name)
        return label, {'passed': passed, 'failed': failed}
    return check


def claude_plugin(work, args, log):
    passed, failed = 0, []
    # A folder with a marketplace.json is checked as a marketplace, so plugin.json gets its own run.
    targets = (('repository', ROOT), ('.claude-plugin/plugin.json', ROOT / '.claude-plugin' / 'plugin.json'),
               ('genealogy-plugin.zip', work / 'plugin' / 'genealogy'))
    for name, folder in targets:
        if run([args.claude, 'plugin', 'validate', '--strict', '--profile', 'directory', str(folder)], 'claude', log):
            passed += 1
        else:
            failed.append(name)
    return 'claude plugin validate', {'passed': passed, 'failed': failed}


CHECKS = [
    per_skill('skills-ref', lambda args, folder: [args.skills_ref, 'validate', str(folder)]),
    per_skill('quick_validate', lambda args, folder: [args.python, args.quick_validate, str(folder)]),
    claude_plugin,
]


def unpack(release, work):
    for path in sorted(Path(release).glob('*.zip')):
        if path.name == COMBINED_ZIP:
            continue
        target = work / ('plugin' if path.name == PLUGIN_ZIP else 'skills')
        with zipfile.ZipFile(path) as archive:
            archive.extractall(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('release', help='folder written by package_skills.py --release')
    parser.add_argument('--skills-ref', default='agentskills', help='skills-ref CLI (default: agentskills)')
    parser.add_argument('--quick-validate', required=True, help="path to Anthropic's quick_validate.py")
    parser.add_argument('--claude', default='claude', help='Claude Code CLI (default: claude)')
    parser.add_argument('--python', default=sys.executable, help='Python with PyYAML, for quick_validate.py')
    parser.add_argument('--log', help='also write every command and its output to this file')
    args = parser.parse_args()
    log = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        unpack(args.release, work)
        summary = dict(check(work, args, log) for check in CHECKS)
    if args.log:
        Path(args.log).write_text('\n\n'.join(log) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 1 if any(result['failed'] for result in summary.values()) else 0


if __name__ == '__main__':
    sys.exit(main())
