#!/usr/bin/env python3
"""Build warns when B will abstain, supports a view margin, scales tile overlap
and prints a short summary by default.

Deterministic: synthetic pages drawn here, no model calls, no network.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

from panel_support import PACKETS

SCRIPT = Path(PACKETS.__file__)


def page(folder, name='page1.png', size=(400, 160)):
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)
    for x in range(0, size[0], 7):
        draw.line((x, 0, x, size[1] - 1), fill=(200, 200, 210))
    draw.text((20, 40), 'antecedent   target', fill='black')
    image.save(folder / name)
    return name


def spec(folder, samples=True):
    name = page(folder)
    target = {'region_id': 'R1', 'page': 1, 'bbox_original': [80, 40, 180, 70],
              'line_bbox_original': [20, 30, 380, 80], 'context_bbox_original': [0, 0, 400, 160],
              'anchor_bbox_original': [20, 40, 80, 70],
              'same_hand_samples': [{'source_id': 'S', 'page': 1, 'sample_id': 'E1', 'bbox_original': [200, 90, 330, 120]}] if samples else []}
    return {'schema_version': '1.2', 'source_id': 'S', 'round': 1, 'script': 'Latin',
            'pages': [{'source_id': 'S', 'page': 1, 'image': name, 'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest(),
                       'source_locator': 'Synthetic source page 1'}],
            'targets': [target]}


def payload(out, manifest, method):
    return json.loads((out / manifest['packets'][method]['inputs']).read_text(encoding='utf-8'))


def asset(out, manifest, method, role):
    return next(a for a in payload(out, manifest, method)['assets'] if a['role'] == role)


def union(views):
    boxes = [v['source_bbox_original'] for v in views]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.p = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, data, *extra):
        path = self.p / 'spec.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return subprocess.run([sys.executable, str(SCRIPT), 'build', str(path), '--out', str(self.p / 'packet'), *extra],
                              capture_output=True, text=True)


class AbstentionWarnings(Base):
    def test_empty_samples_warn_that_b_will_abstain(self):
        manifest = PACKETS.build(spec(self.p, samples=False), self.p, self.p / 'packet')
        self.assertTrue(any('R1' in w and 'B will abstain' in w for w in manifest['warnings']), manifest.get('warnings'))
        saved = json.loads((self.p / 'packet/coordinator-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['warnings'], manifest['warnings'])

    def test_samples_present_gives_no_warning(self):
        manifest = PACKETS.build(spec(self.p), self.p, self.p / 'packet')
        self.assertEqual(manifest['warnings'], [])

    def test_cli_prints_the_warning(self):
        run = self.cli(spec(self.p, samples=False))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('B will abstain on R1', run.stdout)


class Margin(Base):
    def test_margin_pads_target_and_line_from_the_page(self):
        data = spec(self.p)
        data['display'] = {'margin': 0.5}
        out = self.p / 'packet'
        manifest = PACKETS.build(data, self.p, out)
        target = asset(out, manifest, 'A', 'target')
        enlarged = [v for v in target['views'] if v['kind'] == 'enlarged']
        self.assertEqual(target['bbox_original'], [65, 25, 195, 85])
        self.assertEqual(union(enlarged), [65, 25, 195, 85])
        for view in target['views']:
            self.assertEqual(view['transform']['margin'], {'fraction': 0.5, 'pixels': 15, 'requested_bbox_original': [80, 40, 180, 70],
                                                           'padded_bbox_original': [65, 25, 195, 85], 'clamped_to_page': False})
        line = asset(out, manifest, 'C', 'line')
        self.assertEqual(line['bbox_original'], [0, 5, 400, 105])
        self.assertTrue(line['views'][0]['transform']['margin']['clamped_to_page'])
        row = payload(out, manifest, 'B')['targets'][0]
        self.assertEqual(row['bbox_original'], [80, 40, 180, 70])
        self.assertEqual(manifest['review_regions'][0]['bbox_original'], [80, 40, 180, 70])

    def test_no_margin_by_default(self):
        out = self.p / 'packet'
        manifest = PACKETS.build(spec(self.p), self.p, out)
        target = asset(out, manifest, 'A', 'target')
        self.assertEqual(target['bbox_original'], [80, 40, 180, 70])
        self.assertTrue(all('margin' not in v['transform'] for v in target['views']))

    def test_bad_margin_is_rejected(self):
        for bad in (-0.1, 2, True, 'wide'):
            with self.subTest(margin=bad):
                data = spec(self.p)
                data['display'] = {'margin': bad}
                with self.assertRaisesRegex(ValueError, 'margin'):
                    PACKETS.build(data, self.p, self.p / ('packet-' + str(bad)))


class TileOverlap(Base):
    def test_tile_overlap_covers_one_line_height(self):
        name = page(self.p, 'wide.png', (2000, 100))
        data = spec(self.p)
        data['pages'][0].update(image=name, sha256=hashlib.sha256((self.p / name).read_bytes()).hexdigest())
        target = data['targets'][0]
        target.update(bbox_original=[300, 10, 400, 90], line_bbox_original=[0, 0, 2000, 100], context_bbox_original=[0, 0, 2000, 100],
                      anchor_bbox_original=[100, 10, 300, 90])
        target['same_hand_samples'][0]['bbox_original'] = [500, 10, 600, 90]
        out = self.p / 'packet'
        manifest = PACKETS.build(data, self.p, out)
        line = asset(out, manifest, 'C', 'line')
        tiles = [v for v in line['views'] if v['kind'] == 'enlarged']
        self.assertGreater(len(tiles), 1)
        for before, after in zip(tiles, tiles[1:]):
            overlap = before['source_bbox_original'][2] - after['source_bbox_original'][0]
            self.assertGreaterEqual(overlap, 100, 'tile overlap is shorter than one text line')
            self.assertGreaterEqual(after['transform']['tile_overlap'], 200)


class ShortOutput(Base):
    def test_default_stdout_is_a_short_summary(self):
        run = self.cli(spec(self.p, samples=False))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertLess(len(run.stdout.encode()), 4096)
        summary = json.loads(run.stdout)
        manifest = json.loads((self.p / 'packet/coordinator-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['out'], str(self.p / 'packet'))
        self.assertEqual(summary['manifest'], str(self.p / 'packet/coordinator-manifest.json'))
        self.assertEqual(summary['packet_id'], manifest['packet_id'])
        self.assertRegex(summary['packet_digest'], '^[0-9a-f]{64}$')
        self.assertEqual(summary['counts']['regions'], 1)
        self.assertEqual(summary['counts']['methods'], 4)
        self.assertEqual(summary['warnings'], manifest['warnings'])
        self.assertNotIn('inventory', summary)
        self.assertIn('inventory', manifest)

    def test_verbose_prints_the_full_result(self):
        run = self.cli(spec(self.p), '--verbose')
        self.assertEqual(run.returncode, 0, run.stderr)
        full = json.loads(run.stdout)
        self.assertIn('packets', full)
        self.assertIn('inventory', full)


if __name__ == '__main__':
    unittest.main(verbosity=2)
