#!/usr/bin/env python3
"""The same-hand reader (B) is told where the target sits in its line.

B gets the line with the target outlined in red and the preceding word in blue, plus a neutral crop
of the preceding word, and its reading must name that location. A comparison sample that resembles
another word in the line cannot move the reading there. Deterministic: synthetic pages from
tests/fixtures/synthetic_pages.py (invented words), no model calls.
"""
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel_support import PACKETS, PAGES, packet_inputs, pin_pages  # noqa: E402


def inside(box, origin):
    return [box[0] - origin[0], box[1] - origin[1], box[2] - origin[0], box[3] - origin[1]]


class TargetPosition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        one = PAGES.render(1, cls.dir / 'page-1.png')
        PAGES.render(2, cls.dir / 'page-2.png')
        cls.anchor, cls.target = one['words'][0]['bbox'], one['words'][1]['bbox']
        cls.line = [0, min(cls.anchor[1], cls.target[1]) - 40, PAGES.PAGE_SIZE[0], max(cls.anchor[3], cls.target[3]) + 40]
        cls.page = Image.open(cls.dir / 'page-1.png').convert('RGB')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(dir=self.dir)) / 'packets'
        self.spec = {'schema_version': '1.2', 'source_id': 'SYNTHETIC-POSITION', 'script': 'Latin', 'round': 1,
                     'targets': [{'region_id': 'P01-R02', 'page': 1, 'bbox_original': self.target,
                                  'line_bbox_original': self.line, 'context_bbox_original': [0, 0, *PAGES.PAGE_SIZE],
                                  'anchor_bbox_original': self.anchor,
                                  'same_hand_samples': [{'sample_id': 'E1', 'source_id': 'SYNTHETIC-POSITION', 'page': 2,
                                                         'bbox_original': self.anchor}]}],
                     'verified_context': {'language': 'Portuguese', 'clues': []}}
        pin_pages(self.spec, self.dir, {1: 'page-1.png', 2: 'page-2.png'})

    def build(self):
        return PACKETS.build(self.spec, self.dir, self.out)

    def test_b_gets_the_marked_line_and_the_preceding_word(self):
        manifest = self.build()
        folder, data = packet_inputs(self, self.out, manifest, 'B')
        row = data['targets'][0]
        assets = {a['asset_id']: a for a in data['assets']}
        self.assertIn('target_locator_view', row, 'B is not told where the target sits in its line')
        line = assets[row['line_asset']]
        locator = next(v for v in line['views'] if v['view_id'] == row['target_locator_view'])
        self.assertEqual(locator['target_bbox_in_line'], inside(self.target, self.line))
        self.assertEqual(locator['anchor_bbox_in_line'], inside(self.anchor, self.line))
        self.assertFalse(locator['transform']['letter_evidence'])
        with Image.open(folder / locator['file']) as marked:
            marked = marked.convert('RGB')
            x0, y0, x1, y1 = locator['target_bbox_in_line']
            self.assertEqual(marked.getpixel((x0 - 2, (y0 + y1) // 2)), (255, 0, 0), 'target is not outlined in red')
            x0, y0, x1, y1 = locator['anchor_bbox_in_line']
            self.assertEqual(marked.getpixel((x0 - 2, (y0 + y1) // 2)), (0, 0, 255), 'preceding word is not outlined in blue')
        anchor = assets[row['anchor_asset']]
        self.assertEqual(anchor['bbox_original'], self.anchor)
        with Image.open(folder / anchor['original_file']) as crop:
            self.assertIsNone(ImageChops.difference(crop.convert('RGB'), self.page.crop(self.anchor)).getbbox(), 'anchor crop is not the preceding word')

    def reports(self, manifest, location):
        rows = []
        for method in 'ABCD':
            product = {PACKETS.PRODUCTS[method]: 'synthetic evidence'}
            if method == 'B':
                product['target_location'] = location
            if method == 'C':
                product.update(raw_line_output='Moonquill', character_audit=[{'group': 'all', 'verdict': 'uncertain'}])
            asset = manifest['packets'][method]['assets'][0]
            row = {'method_id': method, 'source_id': 'SYNTHETIC-POSITION', 'context_id': 'CTX-' + method,
                   'context_isolation': 'fresh', 'model_identity': 'same-test-model', 'round': 1, 'clue_ids': [],
                   'status': 'completed', 'execution_kind': sorted(PACKETS.EXECUTIONS[method])[-1],
                   'inputs_used': [{'asset_id': asset['asset_id'], 'source_id': asset['source_id'], 'page': asset['page'],
                                    'view_id': asset['views'][0]['view_id']}],
                   'spans': [{'region_id': 'P01-R02', 'reading': 'Moonquill', 'alternatives': [], 'visible_evidence': [],
                              'conflicts': [], 'uncertainty': 'fixture', 'method_product': product}]}
            if 'packet_id' in manifest:
                row['packet_id'] = manifest['packet_id']
            rows.append(row)
        return rows

    def test_b_reading_must_stay_on_the_requested_word(self):
        manifest = self.build()
        right = {'source_id': 'SYNTHETIC-POSITION', 'page': 1, 'bbox_original': self.target, 'preceding_anchor': 'Ulvadine'}
        PACKETS.summarize(manifest, self.reports(manifest, right))
        moved = dict(right, bbox_original=self.anchor, preceding_anchor='line start')
        with self.assertRaisesRegex(ValueError, 'target_location', msg='B moved the target to another word in the line'):
            PACKETS.summarize(manifest, self.reports(manifest, moved))
        with self.assertRaisesRegex(ValueError, 'target_location', msg='B gave no preceding word'):
            PACKETS.summarize(manifest, self.reports(manifest, dict(right, preceding_anchor=' ')))

    def test_anchor_or_line_start_is_required_and_must_precede_the_target(self):
        del self.spec['targets'][0]['anchor_bbox_original']
        with self.assertRaisesRegex(ValueError, 'preceding-word', msg='a target without a position was packed'):
            self.build()
        self.spec['targets'][0]['anchor_bbox_original'] = self.target
        with self.assertRaisesRegex(ValueError, 'before the target', msg='an anchor on the target was accepted'):
            self.build()
        self.assertFalse(self.out.exists())

    def test_brief_fixes_the_target_before_exemplars(self):
        brief = (PACKETS.ROOT / 'references/same-hand.md').read_text(encoding='utf-8')
        self.assertTrue('Locate the target before inspecting exemplars' in brief, 'same-hand brief does not fix the target first')


if __name__ == '__main__':
    unittest.main(verbosity=2)
