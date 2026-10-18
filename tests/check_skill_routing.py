#!/usr/bin/env python3
"""Routing checks on skill descriptions: each entry request has exactly one owner."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASE_START = re.compile(r'\bstart(ing)? a (new )?(genealogy )?case\b', re.I)
OWNER = 'genealogy-mode'
TREE_START = re.compile(r"start my (family )?tree|interview me|/tree\b", re.I)
STORY = re.compile(r'/story\b', re.I)


def descriptions():
    result = {}
    for path in sorted((ROOT / 'skills').glob('*/SKILL.md')):
        front = path.read_text(encoding='utf-8').split('---', 2)[1]
        for line in front.splitlines():
            if line.startswith('description:'):
                result[path.parent.name] = line.split(':', 1)[1].strip().strip('"\'')
    return result


class CaseStartRouting(unittest.TestCase):
    def test_orchestrator_claims_case_start(self):
        self.assertRegex(descriptions()[OWNER], CASE_START)

    def test_no_other_skill_claims_case_start(self):
        claimants = sorted(name for name, text in descriptions().items() if name != OWNER and CASE_START.search(text))
        self.assertEqual(claimants, [])



class ModeRouting(unittest.TestCase):
    def owners(self, pattern):
        return sorted(name for name, text in descriptions().items() if pattern.search(text))

    def test_only_interview_claims_tree_start(self):
        self.assertEqual(self.owners(TREE_START), ['genealogy-interview'])

    def test_only_narrative_claims_story(self):
        self.assertEqual(self.owners(STORY), ['genealogy-narrative'])


if __name__ == '__main__':
    unittest.main()
