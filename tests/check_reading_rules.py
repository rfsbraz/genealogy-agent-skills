#!/usr/bin/env python3
"""Instruction checks for quick reading scope and four-method manuscript reading."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
unittest.TestCase.maxDiff = 0
unittest.TestCase.longMessage = False
SKILLS = ROOT / 'skills'


def read(rel):
    return (SKILLS / rel).read_text(encoding='utf-8')


class QuickReadingScope(unittest.TestCase):
    def test_first_answer_does_not_end_the_entry(self):
        text = read('genealogy-transcribe-quick/SKILL.md')
        self.assertTrue('Finding the requested name or date does not complete the sweep' in text, 'first-hit rule missing')
        self.assertTrue('## Target-entry completion checklist' in text, 'checklist missing')

    def test_checklist_covers_both_parties_witnesses_and_margins(self):
        text = read('genealogy-transcribe-quick/SKILL.md').split('## Target-entry completion checklist', 1)[-1]
        for field in ('all principals', 'witnesses', 'margins', 'both spouses and both sets of parents', 'not yet inspected'):
            with self.subTest(field=field):
                self.assertTrue(field in text, field)


class FourMethodReading(unittest.TestCase):
    BRIEFS = ('stroke-analysis.md', 'same-hand.md', 'line-recognition.md', 'context-decoding.md')

    def test_each_method_has_its_own_brief(self):
        for name in self.BRIEFS + ('common-contract.md', 'research-basis.md', 'packet-helper.md'):
            with self.subTest(brief=name):
                self.assertTrue((SKILLS / 'genealogy-read-manuscripts/references' / name).is_file())
        self.assertTrue((SKILLS / 'genealogy-read-manuscripts/scripts/method_packets.py').is_file())

    def test_skill_lists_four_methods(self):
        text = read('genealogy-read-manuscripts/SKILL.md')
        self.assertEqual(re.findall(r'^\| \*\*([ABCD]):', text, re.M), list('ABCD'))

    def test_agreement_is_not_confidence(self):
        text = read('genealogy-read-manuscripts/SKILL.md')
        self.assertTrue('Do not call 4/4 a probability' in text, 'vote-count rule missing')
        self.assertTrue('Assign confidence from legibility' in text, 'evidence rule missing')
        self.assertTrue('four distinct handwriting methods' in read('genealogy-transcribe-detailed/SKILL.md').split('---', 2)[1], 'detailed description')


    def test_quick_read_rule_names_the_method_ids(self):
        rule = next(line for line in read('genealogy-read-manuscripts/SKILL.md').splitlines()
                    if 'When a quick read already happened in this context' in line)
        for value in ('`not_blind`', '`context`', '`context_isolation=shared`'):
            with self.subTest(value=value):
                self.assertTrue(value in rule, value)

if __name__ == '__main__':
    unittest.main(verbosity=2)
