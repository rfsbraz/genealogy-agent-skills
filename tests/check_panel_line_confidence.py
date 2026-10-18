#!/usr/bin/env python3
"""Whole-line (method C) readings are checked against letter-by-letter evidence before
their confidence counts.

The summary never promotes C's candidate: it queues a coordinator letter review carrying C's raw
output and self-audit plus A/B evidence, even when all methods agree. C must supply its frozen raw
line output and a character audit. Deterministic: fixture readings in
tests/fixtures/line_confidence_cases.json and small generated images, no model calls.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel_support import PACKETS, ROOT, pin_pages  # noqa: E402

CASES = json.loads((ROOT / 'tests/fixtures/line_confidence_cases.json').read_text(encoding='utf-8'))['cases']


class WholeLineLetterCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        p = Path(cls.tmp.name)
        for name in ('target', 'line', 'page', 'sample'):
            Image.new('RGB', (150, 30), 'white').save(p / (name + '.png'))
        box = [0, 0, 150, 30]
        spec = {'schema_version': '1.2', 'source_id': 'SYNTHETIC-LINE', 'script': 'Latin', 'round': 1,
                'targets': [{'region_id': 'R1', 'page': 1, 'target_at_line_start': True, 'bbox_original': box, 'target_image': 'target.png',
                             'line_image': 'line.png', 'line_bbox_original': box,
                             'context_image': 'page.png', 'context_bbox_original': box,
                             'same_hand_samples': [{'sample_id': 'E1', 'source_id': 'SYNTHETIC-LINE', 'page': 2,
                                                    'bbox_original': box, 'image': 'sample.png'}]}]}
        pin_pages(spec, p, {1: 'page.png', 2: 'sample.png'})
        cls.manifest = PACKETS.build(spec, p, p / 'packets')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def reports(self, case, audit=True):
        readings = {'A': case['letters']['A'], 'B': case['letters']['B'], 'C': case['line'], 'D': case['line']}
        rows = []
        for method in 'ABCD':
            reading = readings[method]
            product = {PACKETS.PRODUCTS[method]: 'synthetic ' + method + ' evidence for ' + str(reading)} if reading else {}
            if method == 'B' and reading:
                region = self.manifest['review_regions'][0]
                product['target_location'] = dict({k: region[k] for k in ('source_id', 'page', 'bbox_original')},
                                                  preceding_anchor='line start in fixture')
            if method == 'C' and audit:
                product.update(raw_line_output=case['line'], character_audit=[{'group': 'ending', 'verdict': 'uncertain'}])
            row = {'method_id': method, 'source_id': self.manifest['source_id'], 'context_id': 'CTX-' + method,
                   'context_isolation': 'fresh', 'model_identity': 'same-test-model', 'round': 1, 'clue_ids': [],
                   'status': 'completed' if reading else 'abstained',
                   'execution_kind': sorted(PACKETS.EXECUTIONS[method])[-1],
                   'spans': [{'region_id': 'R1', 'reading': reading, 'alternatives': [], 'visible_evidence': [],
                              'conflicts': [], 'uncertainty': 'fixture', 'method_product': product}] if reading else []}
            if 'packet_id' in self.manifest:
                row['packet_id'] = self.manifest['packet_id']
            asset = (self.manifest['packets'][method].get('assets') or [{}])[0]
            if 'asset_id' in asset:
                row['inputs_used'] = [{'asset_id': asset['asset_id'], 'source_id': asset['source_id'],
                                       'page': asset['page'], 'view_id': asset['views'][0]['view_id']}]
            rows.append(row)
        return rows

    def test_every_line_candidate_waits_for_coordinator_letter_review(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                region = PACKETS.summarize(self.manifest, self.reports(case))['agreement']['R1']
                self.assertTrue('sequence_check' in region, 'summary has no whole-line letter check')
                check = region['sequence_check']
                self.assertEqual(check['status'], 'coordinator_letter_review_required')
                self.assertEqual(check['candidate'], case['line'])
                self.assertEqual(check['raw_line_output'], case['line'])
                self.assertFalse(check['confidence_promotion_allowed_by_summary'])
                self.assertEqual(region['confidence'], 'not_computed')
                if case['letters']['A']:
                    self.assertIn(case['letters']['A'], str(check['local_feature_evidence']))
                else:
                    self.assertFalse(check['local_feature_evidence'], 'an abstaining A must not look like letter support')

    def test_line_reading_needs_raw_output_and_character_audit(self):
        rows = self.reports(CASES[1], audit=False)
        with self.assertRaisesRegex(ValueError, 'raw_line_output', msg='a C reading without raw output was accepted'):
            PACKETS.summarize(self.manifest, rows)
        rows[2]['spans'][0]['method_product']['raw_line_output'] = 'Orlamund'
        with self.assertRaisesRegex(ValueError, 'character_audit', msg='a C reading without a character audit was accepted'):
            PACKETS.summarize(self.manifest, rows)

    def test_briefs_require_the_letter_audit(self):
        line = (PACKETS.ROOT / 'references/line-recognition.md').read_text(encoding='utf-8')
        protocol = (PACKETS.ROOT / 'references/protocol.md').read_text(encoding='utf-8')
        self.assertTrue('character_audit' in line, 'line brief does not ask C for a character audit')
        self.assertTrue('## Mandatory sequence-reading check' in protocol, 'protocol lacks the sequence-reading check')


if __name__ == '__main__':
    unittest.main(verbosity=2)
