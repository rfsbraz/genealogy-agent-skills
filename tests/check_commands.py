#!/usr/bin/env python3
"""Checks for the thin /tree and /story command files and for host-neutral SKILL.md frontmatter."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ROOT / 'commands'
OWNERS = {'tree': 'genealogy-interview', 'story': 'genealogy-narrative'}
SKILL_REF = re.compile(r'\bgenealogy-[a-z]+(?:-[a-z]+)*\b')
# disable-model-invocation is the one allowed exception: it keeps specialist skills user- or mode-invoked
# (see tests/check_packaging.py).
HOST_ONLY_KEYS = {'argument-hint', 'user-invocable', 'allowed-tools', 'model',
                  'context', 'agent', 'hooks', 'arguments', 'when_to_use', 'effort', 'paths', 'shell'}


def frontmatter(text):
    if not text.startswith('---\n'):
        return {}, text
    block, body = text[4:].split('\n---', 1)
    keys = {}
    for line in block.splitlines():
        if line and not line.startswith((' ', '\t')) and ':' in line:
            key, value = line.split(':', 1)
            keys[key.strip()] = value.strip().strip('"\'')
    return keys, body


def toml_strings(text):
    """Read the top-level basic and multi-line string keys of a small command TOML file (3.10 has no tomllib)."""
    values = {}
    for m in re.finditer(r'(?ms)^(\w+)\s*=\s*(?:"""(.*?)"""|"((?:[^"\\]|\\.)*)")', text):
        values[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return values


def skill_names():
    return {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}


class CommandFiles(unittest.TestCase):
    def test_markdown_commands_for_claude_code_and_cursor(self):
        for name, owner in OWNERS.items():
            with self.subTest(command=name):
                keys, body = frontmatter((COMMANDS / f'{name}.md').read_text(encoding='utf-8'))
                self.assertTrue(keys.get('description'))
                self.assertEqual(keys.get('name'), name)
                self.assertIn(owner, body)
                self.assertIn('$ARGUMENTS', body)

    def test_toml_commands_for_gemini(self):
        for name, owner in OWNERS.items():
            with self.subTest(command=name):
                values = toml_strings((COMMANDS / f'{name}.toml').read_text(encoding='utf-8'))
                self.assertTrue(values.get('description'))
                self.assertIn(owner, values.get('prompt', ''))
                self.assertIn('{{args}}', values['prompt'])

    def test_commands_reference_only_existing_skills(self):
        known = skill_names()
        files = sorted(COMMANDS.glob('*'))
        self.assertTrue(files)
        for path in files:
            with self.subTest(file=path.name):
                refs = set(SKILL_REF.findall(path.read_text(encoding='utf-8')))
                self.assertTrue(refs)
                self.assertLessEqual(refs, known)

    def test_cursor_manifest_keeps_default_commands_discovery(self):
        manifest = json.loads((ROOT / '.cursor-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertNotIn('commands', manifest)


class SkillFrontmatterIsHostNeutral(unittest.TestCase):
    def test_no_host_only_keys(self):
        for folder in ('skills', 'evaluation'):
            for path in sorted((ROOT / folder).glob('*/SKILL.md')):
                with self.subTest(skill=path.parent.name):
                    keys, _ = frontmatter(path.read_text(encoding='utf-8'))
                    self.assertEqual(set(keys) & HOST_ONLY_KEYS, set())


if __name__ == '__main__':
    unittest.main()
