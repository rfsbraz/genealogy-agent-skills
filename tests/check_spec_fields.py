#!/usr/bin/env python3
"""Optional Agent Skills spec fields: license, metadata (author, version) and compatibility. No network.

The source SKILL.md files carry license, compatibility and metadata.author. metadata.version is
added at packaging from .release-please-manifest.json, the file release-please bumps, so there is
one source for the version and manifest.json checksums stay valid on release PRs.
"""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def skill_files():
    return sorted(list((ROOT / 'skills').glob('*/SKILL.md')) + list((ROOT / 'evaluation').glob('*/SKILL.md')))


def fields(text):
    """Top-level keys, plus the keys nested under metadata. Values are unquoted; comments dropped."""
    head = text.split('---', 2)[1]
    top, meta, current = {}, {}, None
    for line in head.splitlines():
        match = re.match(r'^(\s*)([A-Za-z][\w-]*):\s*(.*?)\s*(#.*)?$', line)
        if not match:
            continue
        indent, key, value = match.group(1), match.group(2), match.group(3)
        value = json.loads(value) if value.startswith('"') else value
        if indent and current == 'metadata':
            meta[key] = value
        elif not indent:
            current = key
            top[key] = value
    top['metadata'] = meta
    return top


def version():
    return json.loads((ROOT / '.release-please-manifest.json').read_text(encoding='utf-8'))['.']


class SpecFields(unittest.TestCase):
    def test_every_skill_declares_license_and_metadata(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                data = fields(path.read_text(encoding='utf-8'))
                self.assertEqual(data.get('license'), 'MIT')
                self.assertEqual(data['metadata'].get('author'), 'Rodrigo Braz')
                self.assertNotIn('version', data['metadata'], 'the version is stamped at packaging')

    def test_skills_with_scripts_state_their_runtime(self):
        for path in skill_files():
            if not (path.parent / 'scripts').is_dir():
                continue
            with self.subTest(skill=path.parent.name):
                compatibility = fields(path.read_text(encoding='utf-8')).get('compatibility', '')
                self.assertIn('Python 3.10+', compatibility)

    def test_compatibility_fits_the_spec(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                self.assertLessEqual(len(fields(path.read_text(encoding='utf-8')).get('compatibility', '')), 500)

    def test_pillow_is_named_where_packets_need_it(self):
        data = fields((ROOT / 'skills/genealogy-read-manuscripts/SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('Pillow', data['compatibility'])


class VersionSync(unittest.TestCase):
    def test_version_has_one_source(self):
        config = json.loads((ROOT / 'release-please-config.json').read_text(encoding='utf-8'))
        paths = {e['path'] for e in config['packages']['.']['extra-files']}
        self.assertFalse([p for p in paths if p.endswith('SKILL.md')], 'SKILL.md is hashed in manifest.json')


def load_packager():
    spec = importlib.util.spec_from_file_location('package_skills', ROOT / 'scripts' / 'package_skills.py')
    packager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packager)
    return packager


class BundlesKeepTheFields(unittest.TestCase):
    def test_bundles_are_stamped_with_the_release_version(self):
        packager = load_packager()
        packager.version = lambda: '9.9.9'
        with tempfile.TemporaryDirectory() as tmp:
            packager.build(Path(tmp))
            for path in sorted((Path(tmp) / 'skills').glob('*/SKILL.md')):
                with self.subTest(skill=path.parent.name):
                    data = fields(path.read_text(encoding='utf-8'))
                    self.assertEqual(data['metadata'], {'author': 'Rodrigo Braz', 'version': '9.9.9'})

    def test_bundled_frontmatter_keeps_spec_fields(self):
        packager = load_packager()
        with tempfile.TemporaryDirectory() as tmp:
            packager.build(Path(tmp), ['genealogy-read-manuscripts'])
            data = fields((Path(tmp) / 'skills/genealogy-read-manuscripts/SKILL.md').read_text(encoding='utf-8'))
        self.assertEqual(data['license'], 'MIT')
        self.assertEqual(data['metadata']['version'], version())
        self.assertIn('Pillow', data['compatibility'])
        self.assertNotIn('disable-model-invocation', data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
