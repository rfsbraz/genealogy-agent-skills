#!/usr/bin/env python3
"""Packaging checks: skill names, and which skills a host may load on its own. No network."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Only these load on their own; every other skill is invoked by the user or by genealogy-mode.
AUTO_TRIGGER = {'genealogy-mode', 'genealogy-interview', 'genealogy-narrative'}
# Spelled in pieces so this file does not match itself.
OLD_NAMES = re.compile('genealogy-' + 'orchestrator' + r'|(?<![\w-])read-' + 'manuscripts')


def frontmatter(skill):
    head = (skill / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)[1]
    return {k.strip(): v.strip().strip('"\'') for k, v in (line.split(':', 1) for line in head.splitlines() if ':' in line)}


def skills():
    return sorted(p for p in (ROOT / 'skills').iterdir() if (p / 'SKILL.md').is_file())


class SkillNames(unittest.TestCase):
    def test_renamed_skills_exist_and_every_name_matches_its_folder(self):
        names = {p.name for p in skills()}
        self.assertTrue({'genealogy-mode', 'genealogy-read-manuscripts'} <= names, sorted(names))
        for skill in skills():
            with self.subTest(skill=skill.name):
                self.assertEqual(frontmatter(skill).get('name'), skill.name)

    def test_old_names_appear_only_in_the_changelog(self):
        files = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        hits = []
        for rel in files:
            path = ROOT / rel
            if rel == 'CHANGELOG.md' or not path.is_file() or path.suffix in {'.png', '.jpg', '.pdf', '.zip', '.sqlite'}:
                continue
            if OLD_NAMES.search(path.read_text(encoding='utf-8', errors='ignore')):
                hits.append(rel)
        self.assertEqual(hits, [], 'old skill names remain')

    def test_installer_installs_the_new_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--dest', tmp, '--apply'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            installed = {a['skill'] for a in json.loads(result.stdout)['actions']}
            self.assertEqual(installed, {p.name for p in skills()})
            for name in ('genealogy-mode', 'genealogy-read-manuscripts'):
                self.assertTrue((Path(tmp) / name / 'SKILL.md').is_file(), name)


class AutoTrigger(unittest.TestCase):
    def test_only_entry_skills_load_on_their_own(self):
        for skill in skills():
            with self.subTest(skill=skill.name):
                manual = frontmatter(skill).get('disable-model-invocation') == 'true'
                policy = skill / 'agents' / 'openai.yaml'
                explicit = policy.is_file() and re.search(r'^\s*allow_implicit_invocation:\s*false\s*$',
                                                          policy.read_text(encoding='utf-8'), re.M) is not None
                if skill.name in AUTO_TRIGGER:
                    self.assertFalse(manual or explicit, 'entry skill must stay auto-triggered')
                else:
                    self.assertTrue(manual, 'Claude Code and Cursor need disable-model-invocation: true')
                    self.assertTrue(explicit, 'Codex needs policy.allow_implicit_invocation: false')

    def test_mode_loads_specialists_and_gemini_limit_is_stated(self):
        mode = (ROOT / 'skills/genealogy-mode/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('user- or mode-invoked', mode)
        for doc in ('GEMINI.md', 'INSTALL.md'):
            with self.subTest(doc=doc):
                self.assertIn('Gemini CLI cannot enforce', (ROOT / doc).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
