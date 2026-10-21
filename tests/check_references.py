#!/usr/bin/env python3
"""Reference file layout: long references open with a contents list, and every reference is one link from SKILL.md. No network.

Claude may preview a long file with a partial read, so a reference over LONG lines lists its sections
near the top. A reference that links on to another reference is fine only if SKILL.md also links that
second file, so no file is reachable only through a chain.
"""
from pathlib import Path
import posixpath
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LONG = 100
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def skill_files():
    return sorted(list((ROOT / 'skills').glob('*/SKILL.md')) + list((ROOT / 'evaluation').glob('*/SKILL.md')))


def references():
    return sorted(list((ROOT / 'skills').glob('*/references/*.md')) + list((ROOT / 'evaluation').glob('*/references/*.md')))


def reference_links(path):
    """Repository-relative paths of the reference files a Markdown file links to."""
    found = []
    base = path.parent.relative_to(ROOT).as_posix()
    for target in LINK.findall(path.read_text(encoding='utf-8')):
        target = target.split('#', 1)[0]
        if not target or re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I):
            continue
        rel = posixpath.normpath(posixpath.join(base, target))
        if rel.endswith('.md') and '/references/' in rel:
            found.append(rel)
    return found


def slug(heading):
    text = re.sub(r'[`*_]', '', heading.strip().lower())
    text = re.sub(r'[^\w\- ]', '', text)
    return text.replace(' ', '-')


class ContentsLists(unittest.TestCase):
    def test_long_references_open_with_a_contents_list(self):
        for path in references():
            lines = path.read_text(encoding='utf-8').splitlines()
            if len(lines) <= LONG:
                continue
            with self.subTest(reference=path.relative_to(ROOT).as_posix()):
                head = next((line for line in lines[:6] if line.startswith('Contents:')), None)
                self.assertIsNotNone(head, 'needs a "Contents:" line right under the title')
                anchors = re.findall(r'\]\(#([^)]+)\)', head)
                sections = [slug(line[3:]) for line in lines if line.startswith('## ')]
                self.assertEqual(anchors, sections, 'contents must list every ## section in order')


class OneLevelDeep(unittest.TestCase):
    def test_every_reachable_reference_is_linked_from_skill_md(self):
        for skill in skill_files():
            direct = set(reference_links(skill))
            missing, seen, queue = set(), set(), sorted(direct)
            while queue:
                ref = queue.pop()
                if ref in seen or not (ROOT / ref).is_file():
                    continue
                seen.add(ref)
                for onward in reference_links(ROOT / ref):
                    if onward not in direct:
                        missing.add(onward)
                    queue.append(onward)
            with self.subTest(skill=skill.parent.name):
                self.assertEqual(sorted(missing), [], 'link these from SKILL.md too')


if __name__ == '__main__':
    unittest.main(verbosity=2)
