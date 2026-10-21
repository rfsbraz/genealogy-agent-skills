#!/usr/bin/env python3
"""The install smoke test: pinned host CLIs, output parsing and the checks it runs. No network."""
from pathlib import Path
import importlib.util
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'install-smoke.yml'
SCRIPT = ROOT / 'scripts' / 'smoke_install.py'


def load():
    spec = importlib.util.spec_from_file_location('smoke_install', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLAUDE_DETAILS = """Genealogy (genealogy) 9.9.9
  Description: test
  Source: genealogy@genealogy-agent-skills

Component inventory
  Skills (3)  alpha-skill, beta-skill, story
  Agents (0)
"""

GEMINI_LIST = """\u2713 genealogy (9.9.9)
 Path: /tmp/x/.gemini/extensions/genealogy
 Enabled (User): true
 Context files:
  /tmp/x/.gemini/extensions/genealogy/GEMINI.md
 Agent skills:
  alpha-skill: Use when one thing. Not for another: really.
  beta-skill: Use when two things.
"""


class Pins(unittest.TestCase):
    def test_every_host_has_an_exact_version(self):
        smoke = load()
        self.assertEqual(set(smoke.HOSTS), {'claude', 'gemini', 'codex', 'skills'})
        for host, pin in smoke.HOSTS.items():
            with self.subTest(host=host):
                self.assertRegex(pin['version'], r'^\d+\.\d+\.\d+$')

    def test_claude_pin_is_shared_with_the_validators(self):
        smoke = load()
        script = (ROOT / 'scripts' / 'install_host_validators.sh').read_text(encoding='utf-8')
        pinned = re.search(r'^CLAUDE_CODE_VERSION=(\S+)$', script, re.M).group(1)
        self.assertEqual(smoke.HOSTS['claude']['version'], pinned)


class Expectations(unittest.TestCase):
    def test_expected_skills_commands_and_version_come_from_the_repo(self):
        smoke = load()
        skills = sorted(p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md'))
        self.assertEqual(smoke.expected_skills(), skills)
        self.assertEqual(smoke.expected_commands(), ['story', 'tree'])
        self.assertRegex(smoke.expected_version(), r'^\d+\.\d+\.\d+$')


class Parsing(unittest.TestCase):
    def test_claude_details_lists_skills(self):
        self.assertEqual(load().parse_claude_details(CLAUDE_DETAILS), ['alpha-skill', 'beta-skill', 'story'])

    def test_gemini_list_gives_version_path_and_skills(self):
        parsed = load().parse_gemini_list(GEMINI_LIST)
        self.assertEqual(parsed['version'], '9.9.9')
        self.assertEqual(parsed['path'], '/tmp/x/.gemini/extensions/genealogy')
        self.assertTrue(parsed['enabled'])
        self.assertEqual(parsed['skills'], ['alpha-skill', 'beta-skill'])

    def test_gemini_list_without_the_extension(self):
        self.assertIsNone(load().parse_gemini_list('No extensions installed.\n'))


class Comparison(unittest.TestCase):
    def test_missing_and_extra_names_are_reported(self):
        errors = load().compare('skills', ['a', 'c'], ['a', 'b'])
        self.assertEqual(len(errors), 1)
        self.assertIn('missing b', errors[0])
        self.assertIn('unexpected c', errors[0])

    def test_matching_names_pass(self):
        self.assertEqual(load().compare('skills', ['b', 'a'], ['a', 'b']), [])


class Links(unittest.TestCase):
    def test_broken_relative_links_are_found(self):
        smoke = load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'one').mkdir()
            (root / 'one' / 'SKILL.md').write_text(
                '[ok](../two/SKILL.md) [web](https://example.org) [anchor](#x) [bad](../three/SKILL.md#y)\n',
                encoding='utf-8')
            (root / 'two').mkdir()
            (root / 'two' / 'SKILL.md').write_text('[back](../one/SKILL.md)\n', encoding='utf-8')
            broken = smoke.broken_links(root)
        self.assertEqual(len(broken), 1)
        self.assertIn('../three/SKILL.md', broken[0])

    def test_installed_tree_check_needs_every_skill(self):
        smoke = load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'alpha').mkdir()
            (root / 'alpha' / 'SKILL.md').write_text('x\n', encoding='utf-8')
            errors = smoke.check_skill_tree(root, ['alpha', 'beta'])
        self.assertTrue(any('beta' in e for e in errors))


class Workflow(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')

    def test_runs_every_host_on_github_hosted_runners(self):
        for host in ('claude', 'gemini', 'codex', 'skills'):
            self.assertIn(host, self.text)
        runners = re.findall(r'runs-on:\s*(\S+)', self.text)
        self.assertTrue(runners)
        self.assertTrue(all(r == 'ubuntu-latest' for r in runners), runners)
        self.assertIn('scripts/smoke_install.py', self.text)

    def test_runs_nightly_and_on_pull_requests_without_secrets(self):
        self.assertIn('schedule:', self.text)
        self.assertIn('pull_request:', self.text)
        self.assertNotIn('secrets.', self.text)
        self.assertIn('permissions:\n  contents: read', self.text)


class Docs(unittest.TestCase):
    def test_contributing_explains_the_smoke_test(self):
        text = (ROOT / 'CONTRIBUTING.md').read_text(encoding='utf-8')
        self.assertIn('scripts/smoke_install.py', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
