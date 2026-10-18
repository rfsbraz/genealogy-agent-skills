#!/usr/bin/env python3
"""Preflight names valid source quality values, line-start targets need no anchor answer,
and context clues carry their own certainty to method D. Synthetic images only, no model calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_v141 import MODULE  # noqa: E402
from check_v143 import fixture  # noqa: E402

CLUE = {'id': 'C1', 'fact': 'Synthetic register uses a fixed baptism formula.',
        'provenance': 'Synthetic external contextual fixture', 'independent_of_target': True}


class ReviewFields(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.p = Path(self.temp.name)
        self.spec = fixture(self.p); self.gate = MODULE.load_module('packet_review')

    def tearDown(self): self.temp.cleanup()

    def build(self, name='packet'):
        self.m = MODULE.build(self.spec, self.p, self.p / name)
        self.manifest = self.p / name / 'coordinator-manifest.json'
        return self.m

    def template(self):
        return json.loads((self.manifest.parent / 'preflight-template.json').read_text())

    def review(self, **checks):
        record = self.template()
        record.update(reviewed_by='unit-test fixture', reviewed_at='2026-10-17T12:00:00+00:00')
        for region in record['regions']:
            region.update(inspected_files=region['required_files'], source_page_correct=True, target_complete=True,
                          views_usable=True, source_quality='adequate_for_attempt',
                          notes='Synthetic software fixture; not a human image review.')
            region.update(checks)
        return record

    def line_start(self):
        target = self.spec['targets'][0]
        target.pop('anchor_bbox_original'); target['target_at_line_start'] = True
        target['bbox_original'] = [20, 40, 120, 70]
        return self.build()

    def test_source_quality_template_and_error_name_valid_values(self):
        self.build()
        shown = self.template()['regions'][0]['source_quality']
        self.assertIn('adequate_for_attempt', shown); self.assertIn('needs_better_source', shown)
        with self.assertRaises(ValueError) as caught:
            self.gate.assess(self.manifest.parent, self.m, self.review(anchor_correct=True, source_quality=shown))
        self.assertIn('adequate_for_attempt', str(caught.exception))
        self.assertIn('needs_better_source', str(caught.exception))

    def test_line_start_region_uses_line_start_check_not_anchor(self):
        self.line_start()
        region = self.template()['regions'][0]
        self.assertIsNone(region['anchor_correct']); self.assertIn('line_start_correct', region)
        self.assertIsNone(region['line_start_correct'])
        ok = self.gate.assess(self.manifest.parent, self.m, self.review(anchor_correct=None, line_start_correct=True))
        self.assertEqual(ok['status'], 'passed')
        wrong = self.gate.assess(self.manifest.parent, self.m, self.review(anchor_correct=None, line_start_correct=False))
        self.assertEqual(wrong['status'], 'blocked')
        for bad in ({'anchor_correct': None, 'line_start_correct': None}, {'anchor_correct': True, 'line_start_correct': True}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError): self.gate.assess(self.manifest.parent, self.m, self.review(**bad))

    def test_anchored_region_still_needs_anchor_answer(self):
        self.build()
        self.assertNotIn('line_start_correct', self.template()['regions'][0])
        with self.assertRaises(ValueError):
            self.gate.assess(self.manifest.parent, self.m, self.review(anchor_correct=None, line_start_correct=True))
        self.assertEqual(self.gate.assess(self.manifest.parent, self.m, self.review(anchor_correct=True))['status'], 'passed')

    def test_clue_certainty_is_required_and_reaches_d_only(self):
        self.spec['verified_context'] = {'language': 'Portuguese', 'clues': [dict(CLUE)]}
        with self.assertRaisesRegex(ValueError, 'clue_certainty'): self.build('missing')
        self.spec['verified_context']['clues'][0]['clue_certainty'] = 'sure-ish'
        with self.assertRaisesRegex(ValueError, 'clue_certainty'): self.build('invalid')
        self.spec['verified_context']['clues'][0]['clue_certainty'] = 'uncertain'
        self.build()
        for method, packet in self.m['packets'].items():
            inputs = json.loads((self.manifest.parent / packet['inputs']).read_text())
            if method == 'D':
                self.assertEqual(inputs['verified_context']['clues'][0]['clue_certainty'], 'uncertain')
            else:
                self.assertNotIn('verified_context', inputs)


if __name__ == '__main__':
    unittest.main(verbosity=2)
