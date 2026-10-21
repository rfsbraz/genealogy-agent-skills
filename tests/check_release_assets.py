#!/usr/bin/env python3
"""Release assets: per-skill claude.ai zips, the combined zip, the plugin zip and SHA256SUMS. No network."""
import hashlib
import importlib.util
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMBINED = 'genealogy-skills-claude-ai.zip'
PLUGIN = 'genealogy-plugin.zip'


def load_packager():
    spec = importlib.util.spec_from_file_location('package_skills', ROOT / 'scripts' / 'package_skills.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def skills():
    return sorted(p.name for p in (ROOT / 'skills').iterdir() if (p / 'SKILL.md').is_file())


class ReleaseAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.packager = load_packager()
        cls.report = cls.packager.build(Path(cls.tmp.name), release=True)
        cls.release = Path(cls.tmp.name) / 'release'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_asset_names(self):
        expected = sorted([f'{name}.zip' for name in skills()] + [COMBINED, PLUGIN, 'SHA256SUMS'])
        self.assertEqual(sorted(p.name for p in self.release.iterdir()), expected)

    def test_each_skill_zip_has_the_skill_folder_at_its_root(self):
        for name in skills():
            with self.subTest(skill=name), zipfile.ZipFile(self.release / f'{name}.zip') as z:
                names = z.namelist()
                self.assertEqual({n.split('/', 1)[0] for n in names}, {name})
                self.assertIn(f'{name}/SKILL.md', names)
                self.assertNotIn('disable-model-invocation', z.read(f'{name}/SKILL.md').decode('utf-8').split('---', 2)[1])

    def test_combined_zip_holds_one_zip_per_skill(self):
        with zipfile.ZipFile(self.release / COMBINED) as z:
            self.assertEqual(sorted(z.namelist()), [f'{name}.zip' for name in skills()])
            inner = zipfile.ZipFile(io.BytesIO(z.read('genealogy-mode.zip')))
            self.assertIn('genealogy-mode/SKILL.md', inner.namelist())

    def test_plugin_zip_holds_the_plugin(self):
        with zipfile.ZipFile(self.release / PLUGIN) as z:
            names = set(z.namelist())
        for rel in ('.antigravity-plugin/plugin.json', '.claude-plugin/plugin.json', '.claude-plugin/marketplace.json', '.cursor-plugin/plugin.json',
                    'gemini-extension.json', 'commands/tree.md', 'skills/genealogy-mode/SKILL.md', 'LICENSE'):
            with self.subTest(file=rel):
                self.assertIn(f'genealogy/{rel}', names)
        self.assertFalse([n for n in names if n.startswith(('genealogy/tests/', 'genealogy/.github/'))])
        # Plugin hosts read the source frontmatter, so disable-model-invocation stays.
        self.assertTrue(any(n.endswith('genealogy-reporting/SKILL.md') for n in names))

    def test_plugin_cli_runs_from_the_unpacked_zip(self):
        with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(self.release / PLUGIN) as z:
            z.extractall(tmp)
            result = subprocess.run([sys.executable, str(Path(tmp) / 'genealogy' / 'genealogy.py'), 'countries'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_checksums_cover_every_zip(self):
        lines = (self.release / 'SHA256SUMS').read_text(encoding='utf-8').splitlines()
        sums = dict(reversed(re.match(r'^([0-9a-f]{64})  (\S+)$', line).groups()) for line in lines)
        self.assertEqual(sorted(sums), sorted(p.name for p in self.release.glob('*.zip')))
        for name, digest in sums.items():
            with self.subTest(asset=name):
                self.assertEqual(hashlib.sha256((self.release / name).read_bytes()).hexdigest(), digest)

    def test_build_is_reproducible(self):
        with tempfile.TemporaryDirectory() as other:
            self.packager.build(Path(other), release=True)
            again = (Path(other) / 'release' / 'SHA256SUMS').read_text(encoding='utf-8')
        self.assertEqual(again, (self.release / 'SHA256SUMS').read_text(encoding='utf-8'))

    def test_release_check_passes(self):
        self.assertEqual(self.packager.check_release(self.release), [])


class ReleaseWorkflow(unittest.TestCase):
    def test_assets_job_runs_only_when_a_release_is_created(self):
        text = (ROOT / '.github/workflows/release-please.yml').read_text(encoding='utf-8')
        self.assertIn('id: release', text)
        self.assertIn("needs.release-please.outputs.release_created == 'true'", text)
        self.assertIn('python scripts/package_skills.py --release', text)
        self.assertIn('gh release upload', text)
        self.assertNotIn('workflow_dispatch', text)

    def test_install_guide_points_at_the_release_assets(self):
        text = (ROOT / 'INSTALL.md').read_text(encoding='utf-8')
        self.assertIn(COMBINED, text)
        self.assertIn('releases/latest/download/', text)
        self.assertNotIn('zip each folder', text)
        self.assertNotIn('delete the `disable-model-invocation', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
