#!/usr/bin/env python3
"""A story cannot keep citing a reading that a reread has replaced."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_interview_narrative import S, seed, story
from gps_review import evidence_digest


class SupersededReadingInStory(unittest.TestCase):
    def test_story_rejects_superseded_reading(self):
        case = seed()
        draft = story(case)
        self.assertEqual(S.validate_story(case, draft), [])
        old = case['observations'][0]
        new = copy.deepcopy(old)
        new.update(id=old['id'] + '-REREAD', supersedes=old['id'], statement='Corrected synthetic reading.')
        case['observations'].append(new)
        draft['evidence_digest'] = evidence_digest(case)
        errors = S.validate_story(case, draft)
        self.assertTrue(any('superseded' in e for e in errors), errors)

    def test_story_citing_the_replacement_is_fine(self):
        case = seed()
        draft = story(case)
        old = case['observations'][0]
        new = copy.deepcopy(old)
        new.update(id=old['id'] + '-REREAD', supersedes=old['id'])
        case['observations'].append(new)
        for block in draft['blocks']:
            block['observation_ids'] = [new['id'] if o == old['id'] else o for o in block.get('observation_ids', [])]
        draft['evidence_digest'] = evidence_digest(case)
        self.assertFalse(any('superseded' in e for e in S.validate_story(case, draft)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
