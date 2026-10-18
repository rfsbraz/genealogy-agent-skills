#!/usr/bin/env python3
"""Every reading packet carries pre-made enlarged views of each target, with a record of
how each view was made, and each crop really contains its target. No contrast views,
because contrast turns JPEG compression blocks into false strokes.

Deterministic: synthetic pages from tests/fixtures/synthetic_pages.py (invented words at known
boxes), no model calls.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel_support import PACKETS, PAGES, covers, packet_inputs, pin_pages  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def by_region(data, role):
    """Map region ID to that region's asset of the given role."""
    assets = {a['asset_id']: a for a in data['assets']}
    key = {'target': 'target_asset', 'line': 'line_asset', 'context': 'context_asset'}[role]
    return {row['region_id']: assets[row[key]] for row in data['targets'] if key in row}


class TargetViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.layout = PAGES.render(1, cls.dir / 'page.png')
        page = Image.open(cls.dir / 'page.png')
        cls.page = page.convert('RGB')
        targets = []
        words = cls.layout['words']
        for n, word in enumerate(words, 1):
            box = word['bbox']
            row = words[(n - 1) // 2 * 2:(n - 1) // 2 * 2 + 2]  # two words per synthetic row
            page.crop(box).save(cls.dir / ('target-%d.png' % n))
            line = [0, min(w['bbox'][1] for w in row) - 40, PAGES.PAGE_SIZE[0], max(w['bbox'][3] for w in row) + 40]
            page.crop(line).save(cls.dir / ('line-%d.png' % n))
            target = {'region_id': 'P01-R%02d' % n, 'page': 1, 'bbox_original': box,
                      'target_image': 'target-%d.png' % n, 'line_image': 'line-%d.png' % n,
                      'line_bbox_original': line, 'context_image': 'page.png',
                      'context_bbox_original': [0, 0, *PAGES.PAGE_SIZE]}
            if n % 2 == 0:
                target['anchor_bbox_original'] = words[n - 2]['bbox']
            else:
                target['target_at_line_start'] = True
            targets.append(target)
        cls.spec = {'schema_version': '1.2', 'source_id': 'SYNTHETIC-VIEWS', 'script': 'Latin', 'round': 1,
                    'targets': targets,
                    'verified_context': {'language': 'Portuguese', 'clues': []}}
        pin_pages(cls.spec, cls.dir, {1: 'page.png'})
        cls.out = cls.dir / 'packets'
        cls.manifest, cls.error = None, None
        try:
            cls.manifest = PACKETS.build(cls.spec, cls.dir, cls.out)
        except Exception as exc:  # keep the failure visible per test
            cls.error = exc

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def packet(self, method):
        self.assertIsNone(self.error, 'build failed: ' + repr(self.error))
        return packet_inputs(self, self.out, self.manifest, method)

    def test_every_packet_has_neutral_original_and_enlarged_target_views(self):
        for method in 'ABCD':
            folder, data = self.packet(method)
            targets = by_region(data, 'target')
            self.assertEqual(len(targets), len(self.layout['words']))
            for region, asset in targets.items():
                with self.subTest(method=method, region=region):
                    kinds = {v['kind'] for v in asset['views']}
                    self.assertTrue({'original', 'enlarged'} <= kinds, kinds)
                    self.assertNotIn('contrast', kinds)
                    for view in asset['views']:
                        self.assertEqual(sha(folder / view['file']), view['sha256'])
                        self.assertLessEqual(max(view['dimensions']), 1600)

    def test_each_view_records_how_it_was_made_and_can_be_remade(self):
        folder, data = self.packet('A')
        for region, asset in by_region(data, 'target').items():
            with Image.open(folder / asset['original_file']) as source:
                display = source.convert('RGB')
            for view in asset['views']:
                if view['kind'] == 'original':
                    continue
                with self.subTest(region=region, view=view['view_id']):
                    t = view['transform']
                    for key in ('operation', 'scale', 'resampling', 'tile_box_in_resized', 'tool'):
                        self.assertIn(key, t)
                    size = (round(display.width * t['scale'][0]), round(display.height * t['scale'][1]))
                    self.assertEqual(view['kind'], 'enlarged')
                    again = display.resize(size, Image.Resampling.NEAREST).crop(t['tile_box_in_resized'])
                    with Image.open(folder / view['file']) as image:
                        self.assertIsNone(ImageChops.difference(again, image.convert(again.mode)).getbbox(), 'view not reproducible from its record')

    def test_each_crop_contains_its_known_word(self):
        folder, data = self.packet('C')
        targets, lines = by_region(data, 'target'), by_region(data, 'line')
        for n, word in enumerate(self.layout['words'], 1):
            region = 'P01-R%02d' % n
            with self.subTest(word=n):
                asset = targets[region]
                original = next(v for v in asset['views'] if v['kind'] == 'original')
                self.assertTrue(covers(original['source_bbox_original'], word['bbox']), 'target crop does not cover the known word box')
                tiles = [v['source_bbox_original'] for v in asset['views'] if v['kind'] == 'enlarged']
                union = [min(b[0] for b in tiles), min(b[1] for b in tiles), max(b[2] for b in tiles), max(b[3] for b in tiles)]
                self.assertTrue(covers(union, word['bbox']), 'enlarged views do not cover the known word box')
                self.assertTrue(covers(lines[region]['bbox_original'], word['bbox']), 'line crop does not contain the word')
                box = asset['bbox_original']
                inner = [word['bbox'][0] - box[0], word['bbox'][1] - box[1], word['bbox'][2] - box[0], word['bbox'][3] - box[1]]
                image = Image.open(folder / asset['original_file']).convert('RGB')
                self.assertIsNone(ImageChops.difference(image.crop(inner), self.page.crop(word['bbox'])).getbbox(), 'crop pixels differ from the page at the word')
                ink = sum(1 for p in image.crop(inner).convert('L').getdata() if p < 120)
                self.assertGreater(ink, 100, 'no ink inside the cropped word box')

    def test_shared_page_ships_once_per_packet(self):
        folder, data = self.packet('D')
        pages = [a for a in data['assets'] if a['role'] == 'context']
        self.assertEqual(len(pages), 1, 'six targets on one page shipped the page %d times' % len(pages))
        self.assertEqual({row['context_asset'] for row in data['targets']}, {pages[0]['asset_id']})
        for asset in data['assets']:
            boxes = [tuple(v['source_bbox_original']) for v in asset['views'] if v['kind'] != 'original']
            self.assertEqual(len(boxes), len(set(boxes)), 'duplicate views in ' + asset['asset_id'])

    def test_contrast_views_are_refused(self):
        spec = json.loads(json.dumps(self.spec))
        spec['display'] = {'contrast': True}
        with self.assertRaisesRegex(ValueError, 'Contrast views are disabled', msg='a packet with contrast views was built'):
            PACKETS.build(spec, self.dir, self.dir / 'contrast-packets')
        self.assertFalse((self.dir / 'contrast-packets').exists())
        views = PACKETS.load_module('image_views')
        folder = self.dir / 'contrast-direct'
        folder.mkdir()
        record = dict(self.spec['targets'][0], role='target', source_id='SYNTHETIC-VIEWS', sample_id='P01-R01-target',
                      image='target-1.png')
        with self.assertRaisesRegex(ValueError, 'Contrast views are disabled'):
            views.make_views(record, self.dir, folder, 'asset-001', contrast=True)

    def test_target_outside_its_line_crop_is_rejected(self):
        spec = json.loads(json.dumps(self.spec))
        spec['targets'] = spec['targets'][:1]
        word = spec['targets'][0]['bbox_original']
        line = [0, word[3] + 10, PAGES.PAGE_SIZE[0], word[3] + 90]
        Image.open(self.dir / 'page.png').crop(line).save(self.dir / 'line-below.png')
        spec['targets'][0].update(line_image='line-below.png', line_bbox_original=line)
        with self.assertRaisesRegex(ValueError, 'contained', msg='a target outside its line crop was packed'):
            PACKETS.build(spec, self.dir, self.dir / 'outside-packets')


if __name__ == '__main__':
    unittest.main(verbosity=2)
