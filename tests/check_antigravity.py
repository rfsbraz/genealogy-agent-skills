#!/usr/bin/env python3
"""Native Antigravity manifest (.antigravity-plugin/plugin.json) and its install docs. No network.

agy 1.4.4 reads .antigravity-plugin/plugin.json before the root plugin.json, and `agy plugin validate`
warns about any field outside KNOWN_FIELDS.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.antigravity-plugin' / 'plugin.json'
KNOWN_FIELDS = {'name', 'displayName', 'version', 'description', 'logo', 'suggestedPrompts', 'keywords',
                'author', 'homepage', 'repository', 'license'}
INSTALL = 'agy plugin install https://github.com/rfsbraz/genealogy-agent-skills'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


class Manifest(unittest.TestCase):
    def test_manifest_matches_the_other_hosts(self):
        data, root = load(MANIFEST), load(ROOT / 'plugin.json')
        self.assertEqual(data['name'], root['name'])
        self.assertEqual(data['description'], root['description'])
        self.assertEqual(data['version'], load(ROOT / '.release-please-manifest.json')['.'])
        self.assertEqual(data['displayName'], 'Genealogy')

    def test_only_fields_agy_reads(self):
        self.assertLessEqual(set(load(MANIFEST)), KNOWN_FIELDS)

    def test_logo_and_prompts(self):
        data = load(MANIFEST)
        self.assertTrue((ROOT / data['logo']).is_file())
        self.assertTrue(1 <= len(data['suggestedPrompts']) <= 4)

    def test_release_please_bumps_the_version(self):
        config = load(ROOT / 'release-please-config.json')
        self.assertIn({'type': 'json', 'path': '.antigravity-plugin/plugin.json', 'jsonpath': '$.version'},
                      config['packages']['.']['extra-files'])

    def test_plugin_zip_carries_the_manifest(self):
        text = (ROOT / 'scripts' / 'package_skills.py').read_text(encoding='utf-8')
        self.assertIn("'.antigravity-plugin'", text)


class Docs(unittest.TestCase):
    def test_install_steps_use_the_native_plugin(self):
        for doc in ('README.md', 'INSTALL.md'):
            with self.subTest(doc=doc):
                text = (ROOT / doc).read_text(encoding='utf-8')
                self.assertIn(INSTALL, text)
                self.assertNotIn('agy plugin import gemini', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
