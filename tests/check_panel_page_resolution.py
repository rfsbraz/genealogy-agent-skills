#!/usr/bin/env python3
"""The whole-page reader (D) keeps the full-resolution page plus line and target close-ups.

Deterministic: synthetic pages from tests/fixtures/synthetic_pages.py (invented words), no model calls.
The page is pinned by hash and frozen; its full-resolution pixels always ship to D. A reduced page
overview may exist, but only for orientation.
"""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel_support import PACKETS, PAGES, packet_inputs, pin_pages  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class WholePageResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        layout = PAGES.render(1, cls.dir / 'page.png')
        page = Image.open(cls.dir / 'page.png')
        page.resize((page.width // 2, page.height // 2), Image.LANCZOS).save(cls.dir / 'page-half.png')
        cls.target = layout['words'][2]['bbox']
        crop = page.crop(cls.target)
        crop.save(cls.dir / 'target.png')
        crop.resize((crop.width // 2, crop.height // 2), Image.LANCZOS).save(cls.dir / 'target-half.png')
        cls.line = [0, cls.target[1] - 40, PAGES.PAGE_SIZE[0], cls.target[3] + 40]
        page.crop(cls.line).save(cls.dir / 'line.png')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(dir=self.dir)) / 'packets'
        self.spec = {'schema_version': '1.2', 'source_id': 'SYNTHETIC-PAGE', 'script': 'Latin', 'round': 1,
                     'targets': [{'region_id': 'P01-R01', 'page': 1, 'target_at_line_start': True, 'bbox_original': self.target,
                                  'target_image': 'target.png', 'line_image': 'line.png', 'line_bbox_original': self.line,
                                  'context_image': 'page.png', 'context_bbox_original': [0, 0, *PAGES.PAGE_SIZE]}],
                     'verified_context': {'language': 'Portuguese', 'clues': []}}
        pin_pages(self.spec, self.dir, {1: 'page.png'})

    def test_whole_page_reader_gets_full_page_and_full_resolution_details(self):
        manifest = PACKETS.build(self.spec, self.dir, self.out)
        folder, data = packet_inputs(self, self.out, manifest, 'D')
        assets = {a['role']: a for a in data['assets']}
        self.assertEqual(set(assets), {'target', 'line', 'context'})
        page = assets['context']
        self.assertEqual(page['original_dimensions'], list(PAGES.PAGE_SIZE))
        self.assertEqual(sha(folder / page['original_file']), page['original_sha256'])
        full = Image.open(folder / page['original_file']).convert('RGB')
        self.assertIsNone(ImageChops.difference(full, Image.open(self.dir / 'page.png').convert('RGB')).getbbox(), 'whole-page pixels differ from the page')
        self.assertEqual(page['source_page_sha256'], sha(self.dir / 'page.png'))
        source = next(s for s in manifest['sources'] if s['page'] == 1)
        self.assertEqual((self.out / source['file']).read_bytes(), (self.dir / 'page.png').read_bytes(), 'frozen source is not the page bytes')
        overview = [v for v in page['views'] if v['kind'] == 'overview']
        self.assertTrue(all(v['transform'].get('orientation_only') for v in overview), 'a reduced page view is not marked orientation only')
        target = assets['target']
        self.assertEqual(target['original_dimensions'], [self.target[2] - self.target[0], self.target[3] - self.target[1]])
        crop = Image.open(folder / target['original_file']).convert('RGB')
        same = Image.open(self.dir / 'page.png').convert('RGB').crop(self.target)
        self.assertIsNone(ImageChops.difference(crop, same).getbbox(), 'target close-up differs from the page pixels')
        self.assertIn('enlarged', {v['kind'] for v in target['views']})
        self.assertIn('enlarged', {v['kind'] for v in assets['line']['views']})

    def test_half_size_page_is_rejected(self):
        self.spec['targets'][0]['context_image'] = 'page-half.png'
        with self.assertRaisesRegex(ValueError, 'differ from bbox_original', msg='a half-size page was packed for the whole-page reader'):
            PACKETS.build(self.spec, self.dir, self.out)
        self.assertFalse(self.out.exists())

    def test_half_size_target_crop_is_rejected(self):
        self.spec['targets'][0]['target_image'] = 'target-half.png'
        with self.assertRaisesRegex(ValueError, 'differ from bbox_original', msg='a half-size target crop was packed'):
            PACKETS.build(self.spec, self.dir, self.out)

    def test_page_without_its_original_box_is_rejected(self):
        del self.spec['targets'][0]['context_bbox_original']
        # v1.4.2 requires the box; a missing key fails before output (the CLI reports it as a JSON error).
        with self.assertRaises((ValueError, KeyError), msg='a page without context_bbox_original was packed'):
            PACKETS.build(self.spec, self.dir, self.out)
        self.assertFalse(self.out.exists())

    def test_brief_sends_the_reader_to_the_close_ups(self):
        brief = (PACKETS.ROOT / 'references/context-decoding.md').read_text(encoding='utf-8')
        self.assertTrue('original/enlarged line and target views' in brief, 'context brief does not send D to the close-ups')


if __name__ == '__main__':
    unittest.main(verbosity=2)
