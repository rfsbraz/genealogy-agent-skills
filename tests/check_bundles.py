#!/usr/bin/env python3
"""Built skill bundles are self-contained: every relative link resolves inside its own bundle. No network."""
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def load_packager():
    spec = importlib.util.spec_from_file_location('package_skills', ROOT / 'scripts' / 'package_skills.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def relative_links(text):
    for target in LINK.findall(text):
        if re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I) or target.startswith(('#', '/')):
            continue
        yield target.split('#', 1)[0]


def broken_links(bundle):
    """Links in any Markdown file of the bundle that point outside it or at nothing."""
    bundle = bundle.resolve()
    problems = []
    for doc in sorted(bundle.rglob('*.md')):
        for target in relative_links(doc.read_text(encoding='utf-8')):
            if not target:
                continue
            resolved = (doc.parent / target).resolve()
            rel = doc.relative_to(bundle).as_posix()
            if bundle not in resolved.parents and resolved != bundle:
                problems.append(f'{rel}: {target} leaves the bundle')
            elif not resolved.exists():
                problems.append(f'{rel}: {target} does not exist')
    return problems


class BuiltBundles(unittest.TestCase):
    """Builds every bundle once per test class into a temp folder."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.packager = load_packager()
        cls.report = cls.packager.build(cls.out)
        cls.skills = sorted(p.name for p in (ROOT / 'skills').iterdir() if (p / 'SKILL.md').is_file())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def bundle(self, name):
        return self.out / 'skills' / name


class SelfContainedBundles(BuiltBundles):
    def test_one_bundle_per_runtime_skill(self):
        built = sorted(p.name for p in (self.out / 'skills').iterdir())
        self.assertEqual(built, self.skills)
        self.assertEqual(sorted(b['skill'] for b in self.report['bundles']), self.skills)

    def test_every_relative_link_resolves_inside_its_bundle(self):
        for name in self.skills:
            with self.subTest(skill=name):
                self.assertEqual(broken_links(self.bundle(name)), [])

    def test_shared_references_are_copies_of_the_single_source(self):
        copy = self.bundle('genealogy-reporting') / 'shared' / 'genealogy-mode' / 'references' / 'shared-contract.md'
        source = ROOT / 'skills' / 'genealogy-mode' / 'references' / 'shared-contract.md'
        self.assertEqual(copy.read_bytes(), source.read_bytes())
        self.assertFalse((ROOT / 'skills' / 'genealogy-reporting' / 'shared').exists(), 'copies live only in the build')

    def test_narrative_helper_runs_without_sibling_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            alone = Path(tmp) / 'genealogy-narrative'
            subprocess.run(['cp', '-r', str(self.bundle('genealogy-narrative')), str(alone)], check=True)
            result = subprocess.run([sys.executable, str(alone / 'scripts' / 'story_tools.py'), '--help'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_skills_still_point_at_the_coordinator(self):
        # Plugin installs keep sibling folders, so the source keeps one copy of each shared file.
        text = (ROOT / 'skills' / 'genealogy-reporting' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('../genealogy-mode/references/shared-contract.md', text)


SPEC_KEYS = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}


def frontmatter_keys(skill_md):
    head = skill_md.read_text(encoding='utf-8').split('---', 2)[1]
    return {line.split(':', 1)[0] for line in head.splitlines() if re.match(r'^[A-Za-z][\w-]*:', line)}


class BundleFrontmatter(BuiltBundles):
    """claude.ai and the Agent Skills spec accept only SPEC_KEYS; Claude Code still needs disable-model-invocation."""

    def test_bundles_carry_only_spec_keys(self):
        for name in self.skills:
            with self.subTest(skill=name):
                self.assertLessEqual(frontmatter_keys(self.bundle(name) / 'SKILL.md'), SPEC_KEYS)

    def test_source_keeps_the_claude_code_key(self):
        kept = [n for n in self.skills if 'disable-model-invocation' in frontmatter_keys(ROOT / 'skills' / n / 'SKILL.md')]
        self.assertEqual(len(kept), 23)

    def test_only_the_frontmatter_changes(self):
        for name in self.skills:
            with self.subTest(skill=name):
                source = (ROOT / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)
                built = (self.bundle(name) / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)
                self.assertEqual([l for l in source[1].splitlines() if not l.startswith('disable-model-invocation:')],
                                 [l for l in built[1].splitlines() if not l.startswith('  version: ')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
