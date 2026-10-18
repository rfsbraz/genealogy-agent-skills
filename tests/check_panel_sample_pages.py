#!/usr/bin/env python3
"""Every same-hand comparison sample carries its own page identity.

Deterministic: synthetic pages from tests/fixtures/synthetic_pages.py (invented words), no model calls.
The page pair puts two samples with the same sample ID at identical coordinates on different pages,
the case that made one reader discard all samples as contradictory.
"""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel_support import PACKETS, PAGES, packet_inputs, pin_pages  # noqa: E402


def union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SamplePages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        one = PAGES.render(1, cls.dir / 'page-1.png')
        two = PAGES.render(2, cls.dir / 'page-2.png')
        # Same coordinates on both pages: the first word slot is shared by layout.
        cls.box = union(one['words'][0]['bbox'], two['words'][0]['bbox'])
        for page in (1, 2):
            Image.open(cls.dir / ('page-%d.png' % page)).crop(cls.box).save(cls.dir / ('sample-p%d.png' % page))
        cls.target = one['words'][2]['bbox']
        Image.open(cls.dir / 'page-1.png').crop(cls.target).save(cls.dir / 'target.png')
        cls.line = [0, cls.target[1] - 40, PAGES.PAGE_SIZE[0], cls.target[3] + 40]
        Image.open(cls.dir / 'page-1.png').crop(cls.line).save(cls.dir / 'line.png')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(dir=self.dir)) / 'packets'
        sample = lambda page: {'sample_id': 'S1', 'source_id': 'SYNTHETIC-PAIR', 'page': page,
                               'bbox_original': list(self.box), 'image': 'sample-p%d.png' % page}
        self.spec = {'schema_version': '1.2', 'source_id': 'SYNTHETIC-PAIR', 'script': 'Latin', 'round': 1,
                     'targets': [{'region_id': 'P01-R01', 'page': 1, 'target_at_line_start': True, 'bbox_original': self.target,
                                  'target_image': 'target.png', 'line_image': 'line.png', 'line_bbox_original': self.line,
                                  'context_image': 'page-1.png', 'context_bbox_original': [0, 0, *PAGES.PAGE_SIZE],
                                  'same_hand_samples': [sample(1), sample(2)]}],
                     'verified_context': {'language': 'Portuguese', 'clues': []}}
        pin_pages(self.spec, self.dir, {1: 'page-1.png', 2: 'page-2.png'})

    def test_same_coordinates_on_two_pages_stay_distinct_and_page_referenced(self):
        manifest = PACKETS.build(self.spec, self.dir, self.out)
        folder, data = packet_inputs(self, self.out, manifest, 'B')
        samples = [a for a in data['assets'] if a.get('role') == 'exemplar']
        self.assertEqual([a['page'] for a in samples], [1, 2])
        self.assertEqual([a['bbox_original'] for a in samples], [self.box, self.box])
        self.assertEqual([a['sample_id'] for a in samples], ['S1', 'S1'])
        self.assertEqual(len({a['asset_id'] for a in samples}), 2)
        self.assertEqual(len(data['targets'][0]['same_hand_samples']), 2)
        for asset in samples:
            with self.subTest(page=asset['page']):
                self.assertEqual(asset['source_id'], 'SYNTHETIC-PAIR')
                self.assertEqual(asset['source_page_sha256'], sha(self.dir / ('page-%d.png' % asset['page'])))
                with Image.open(folder / asset['original_file']) as crop, Image.open(self.dir / ('sample-p%d.png' % asset['page'])) as own:
                    self.assertIsNone(ImageChops.difference(crop.convert('RGB'), own.convert('RGB')).getbbox(), 'sample pixels come from the wrong page')
                self.assertEqual(sha(folder / asset['original_file']), asset['original_sha256'])
                for view in asset['views']:
                    self.assertTrue(view['view_id'].startswith(asset['asset_id']))

    def test_sample_without_a_page_is_rejected(self):
        del self.spec['targets'][0]['same_hand_samples'][1]['page']
        with self.assertRaises((ValueError, KeyError), msg='a same-hand sample without a page was accepted'):
            PACKETS.build(self.spec, self.dir, self.out)
        self.assertFalse(self.out.exists())

    def test_coordinates_only_samples_are_rejected(self):
        target = self.spec['targets'][0]
        target.pop('same_hand_samples')
        target['same_hand_images'] = ['sample-p1.png', 'sample-p2.png']
        target['same_hand_bboxes_original'] = [self.box, self.box]
        with self.assertRaisesRegex(ValueError, 'page-qualified same_hand_samples', msg='same-hand samples without pages were accepted'):
            PACKETS.build(self.spec, self.dir, self.out)

    def test_one_sample_id_on_one_page_cannot_name_two_crops(self):
        samples = self.spec['targets'][0]['same_hand_samples']
        moved = dict(samples[0]); moved['bbox_original'] = [self.box[0] + 1, self.box[1], self.box[2] + 1, self.box[3]]
        Image.open(self.dir / 'page-1.png').crop(moved['bbox_original']).save(self.dir / 'sample-p1-moved.png')
        moved['image'] = 'sample-p1-moved.png'
        samples.append(moved)
        with self.assertRaisesRegex(ValueError, 'conflicting crops', msg='one sample ID named two crops on one page'):
            PACKETS.build(self.spec, self.dir, self.out)

    def test_brief_says_equal_coordinates_on_other_pages_are_distinct(self):
        brief = (PACKETS.ROOT / 'references/same-hand.md').read_text(encoding='utf-8')
        self.assertTrue('Equal coordinates on different pages' in brief, 'same-hand brief does not explain page identity')


if __name__ == '__main__':
    unittest.main(verbosity=2)
