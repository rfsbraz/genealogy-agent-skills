#!/usr/bin/env python3
"""Repository-level checks: skill frontmatter, Markdown links, manifests and versions."""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIRS = ('skills', 'evaluation')
MANIFESTS = (
    'plugin.json',
    '.cursor-plugin/plugin.json',
    '.claude-plugin/plugin.json',
    '.claude-plugin/marketplace.json',
    '.antigravity-plugin/plugin.json',
    '.agents/plugins/marketplace.json',
    'gemini-extension.json',
)
VERSIONED = ('plugin.json', '.cursor-plugin/plugin.json', '.claude-plugin/plugin.json', '.antigravity-plugin/plugin.json',
             'gemini-extension.json', 'manifest.json')
DESCRIPTION_BUDGET = 8000
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')


def skill_files():
    files = []
    for folder in SKILL_DIRS:
        files.extend(sorted((ROOT / folder).glob('*/SKILL.md')))
    return files


def frontmatter(path):
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise ValueError('no frontmatter')
    block = text[4:].split('\n---', 1)[0]
    data = {}
    for line in block.splitlines():
        if not line.strip() or line.startswith((' ', '\t')):
            continue
        key, _, value = line.partition(':')
        data[key.strip()] = value.strip().strip('"\'')
    return data


def tracked_markdown():
    try:
        out = subprocess.run(['git', 'ls-files', '*.md'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        return [ROOT / p for p in out.splitlines() if p]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob('*.md') if '.git' not in p.parts]


class SkillFrontmatter(unittest.TestCase):
    def test_skills_found(self):
        self.assertGreater(len(skill_files()), 0)

    def test_frontmatter(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                data = frontmatter(path)
                self.assertLessEqual(set(data) - {'name', 'description'}, {'disable-model-invocation'})
                self.assertIn(data.get('disable-model-invocation', 'true'), {'true'})
                self.assertEqual(data['name'], path.parent.name)
                self.assertRegex(data['name'], r'^[a-z0-9]+(-[a-z0-9]+)*$')
                self.assertLessEqual(len(data['name']), 64)
                self.assertTrue(data['description'])
                self.assertLessEqual(len(data['description']), 1024)

    def test_description_budget(self):
        total = sum(len(frontmatter(p)['description']) for p in skill_files())
        self.assertLess(total, DESCRIPTION_BUDGET)


class MarkdownLinks(unittest.TestCase):
    def test_relative_links_resolve(self):
        for path in tracked_markdown():
            text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
            for target in LINK.findall(text):
                if re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I) or target.startswith('#'):
                    continue
                rel = target.split('#', 1)[0]
                if not rel:
                    continue
                with self.subTest(file=path.relative_to(ROOT).as_posix(), link=rel):
                    self.assertTrue((path.parent / rel).exists())


class Manifests(unittest.TestCase):
    def present(self, names):
        return [n for n in names if (ROOT / n).exists()]

    def test_manifests_parse(self):
        for name in self.present(MANIFESTS + ('manifest.json',)):
            with self.subTest(manifest=name):
                json.loads((ROOT / name).read_text(encoding='utf-8'))

    def test_versions_match(self):
        release = ROOT / '.release-please-manifest.json'
        if not release.exists():
            self.skipTest('no .release-please-manifest.json yet')
        expected = json.loads(release.read_text(encoding='utf-8'))['.']
        for name in self.present(VERSIONED):
            with self.subTest(manifest=name):
                self.assertEqual(json.loads((ROOT / name).read_text(encoding='utf-8'))['version'], expected)

    def test_claude_marketplace_name(self):
        market, plugin = ROOT / '.claude-plugin/marketplace.json', ROOT / '.claude-plugin/plugin.json'
        if not (market.exists() and plugin.exists()):
            self.skipTest('no Claude plugin manifests yet')
        name = json.loads(plugin.read_text(encoding='utf-8'))['name']
        entries = [p['name'] for p in json.loads(market.read_text(encoding='utf-8'))['plugins']]
        self.assertIn(name, entries)


GENERIC_VERSIONED = ('INSTALL.md', 'README.md')
VERSION_MARKER = 'x-release-please-version'


def copy_repo(dest):
    """Copy the working tree and regenerate its manifest, so each test starts from a current manifest."""
    import shutil
    import sys
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
    subprocess.run([sys.executable, 'scripts/build_manifest.py'], cwd=dest, capture_output=True, check=True)


def bump(root, version):
    """Apply a release the way release-please would: release manifest, JSON extra-files and marked lines."""
    config = json.loads((root / 'release-please-config.json').read_text(encoding='utf-8'))
    (root / '.release-please-manifest.json').write_text(json.dumps({'.': version}, indent=2) + '\n', encoding='utf-8')
    for entry in config['packages']['.']['extra-files']:
        path = root / entry['path']
        text = path.read_text(encoding='utf-8')
        if entry.get('type') == 'json':
            data = json.loads(text)
            data['version'] = version
            text = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
        else:
            text = '\n'.join(re.sub(r'\d+\.\d+\.\d+', version, line) if VERSION_MARKER in line else line
                             for line in text.split('\n'))
        path.write_text(text, encoding='utf-8')


class ReleasePlease(unittest.TestCase):
    def config(self):
        return json.loads((ROOT / 'release-please-config.json').read_text(encoding='utf-8'))

    def test_config_shape(self):
        config = self.config()
        package = config['packages']['.']
        self.assertEqual(package.get('release-type', config.get('release-type')), 'simple')
        self.assertNotIn('bootstrap-sha', config)
        self.assertEqual(list(json.loads((ROOT / '.release-please-manifest.json').read_text(encoding='utf-8'))), ['.'])

    def test_extra_files_cover_every_version_field(self):
        entries = self.config()['packages']['.']['extra-files']
        json_files = {e['path'] for e in entries if e.get('type') == 'json' and e.get('jsonpath') == '$.version'}
        generic = {e['path'] for e in entries if e.get('type') == 'generic'}
        self.assertEqual(json_files, set(VERSIONED))
        self.assertEqual(generic, set(GENERIC_VERSIONED))

    def test_marked_lines_carry_the_release_version(self):
        version = json.loads((ROOT / '.release-please-manifest.json').read_text(encoding='utf-8'))['.']
        for name in GENERIC_VERSIONED:
            with self.subTest(doc=name):
                lines = [l for l in (ROOT / name).read_text(encoding='utf-8').splitlines() if VERSION_MARKER in l]
                self.assertEqual(len(lines), 1)
                self.assertIn(version, lines[0])

    def test_build_manifest_reads_release_version(self):
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            copy_repo(root)
            (root / '.release-please-manifest.json').write_text('{\n  ".": "9.9.9"\n}\n', encoding='utf-8')
            check = subprocess.run([sys.executable, 'scripts/build_manifest.py', '--check'], cwd=root,
                                   capture_output=True, text=True)
            self.assertEqual(check.returncode, 1, check.stdout)

    def test_release_branch_keeps_manifest_current(self):
        import sys
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            copy_repo(root)
            bump(root, '9.9.9')
            check = subprocess.run([sys.executable, 'scripts/build_manifest.py', '--check'], cwd=root,
                                   capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            for name in VERSIONED:
                self.assertEqual(json.loads((root / name).read_text(encoding='utf-8'))['version'], '9.9.9')


class PrivacyScope(unittest.TestCase):
    def test_privacy_scan_covers_examples(self):
        import os
        import sys
        env = dict(os.environ, PRIVACY_DENYLIST='CASE-SYNTHETIC-BEATRIZ')
        out = subprocess.run([sys.executable, 'scripts/privacy_scan.py'], cwd=ROOT, env=env,
                             capture_output=True, text=True).stdout
        self.assertRegex(out, r'(?m)^examples/v1\.3/narrative/case\.json:\d+: denylist$', msg=out[-500:])


class UserDocs(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding='utf-8')

    def test_readme_and_install_cover_interview_and_story(self):
        for name in ('README.md', 'INSTALL.md'):
            text = self.read(name)
            with self.subTest(doc=name):
                self.assertIn('Interview me to start my family tree', text)
                self.assertIn('genealogy-interview', text)
                self.assertIn('genealogy-narrative', text)
                self.assertIn('/tree', text)
                self.assertIn('/story', text)
                self.assertIn('docs/workflows/modes.md', text)

    def test_changelog_covers_current_and_previous_release(self):
        version = json.loads(self.read('manifest.json'))['version']
        headings = re.findall(r'^## \[?(\d+\.\d+\.\d+)', self.read('CHANGELOG.md'), re.M)
        self.assertEqual(headings[:1], [version])
        self.assertIn('1.2.0', headings)

    def test_no_em_dashes_in_user_docs(self):
        for name in ('README.md', 'INSTALL.md', 'CHANGELOG.md'):
            with self.subTest(doc=name):
                self.assertNotIn('\u2014', self.read(name))


class SkillFlow(unittest.TestCase):
    NODE = re.compile(r'\b[A-Z]+\["([^"]+)"\]')

    def labels(self):
        return self.NODE.findall((ROOT / 'docs/skill-flow.mmd').read_text(encoding='utf-8'))

    def test_readme_embeds_the_skill_flow(self):
        self.assertIn('](docs/assets/skill-flow.svg)', (ROOT / 'README.md').read_text(encoding='utf-8'))

    def test_skill_flow_has_one_box_per_skill(self):
        boxes = sorted(label.split(':')[0].removeprefix('genealogy-') for label in self.labels()
                       if not label.startswith(('You', '/')))
        skills = sorted(p.name.removeprefix('genealogy-') for p in (ROOT / 'skills').glob('genealogy-*') if p.is_dir())
        self.assertEqual(boxes, skills)

    def test_skill_flow_svg_matches_source(self):
        # Labels must be plain SVG text, not HTML in foreignObject, so every viewer shows them.
        import xml.etree.ElementTree as ET
        svg = (ROOT / 'docs/assets/skill-flow.svg').read_text(encoding='utf-8')
        self.assertFalse('foreignObject' in svg, 'regenerate with -c docs/mermaid-config.json')
        self.assertTrue('background-color: white' in svg, 'regenerate with -b white')
        ns = '{http://www.w3.org/2000/svg}'
        texts = {' '.join(' '.join(node.itertext()).split()) for node in ET.fromstring(svg).iter(ns + 'text')}
        missing = [label for label in self.labels() if label not in texts]
        self.assertEqual(missing, [], 'regenerate docs/assets/skill-flow.svg from docs/skill-flow.mmd')


if __name__ == '__main__':
    unittest.main()
