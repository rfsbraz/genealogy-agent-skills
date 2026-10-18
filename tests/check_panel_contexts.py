#!/usr/bin/env python3
"""The four-method panel stops when readers did not run in separate contexts.

Deterministic: synthetic reports only, no images, no model calls.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('method_packets', ROOT / 'skills/genealogy-read-manuscripts/scripts/method_packets.py')
PACKETS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PACKETS)


def manifest():
    return {'source_id': 'SYNTHETIC-PANEL', 'round': 1, 'planned_methods': list('ABCD'),
            'packets': {m: {'regions': ['R1']} for m in 'ABCD'}}


def reports():
    rows = []
    for method in 'ABCD':
        rows.append({'method_id': method, 'context_id': 'CTX-' + method, 'context_isolation': 'fresh',
                     'model_identity': 'same-test-model', 'round': 1, 'clue_ids': [], 'status': 'completed',
                     'execution_kind': sorted(PACKETS.EXECUTIONS[method])[-1],
                     'spans': [{'region_id': 'R1', 'reading': 'Ulvadine', 'alternatives': [],
                                'visible_evidence': [], 'conflicts': [], 'uncertainty': 'fixture',
                                'method_product': {PACKETS.PRODUCTS[method]: 'synthetic product'}}]})
    return rows


class PanelNeedsSeparateContexts(unittest.TestCase):
    def assertPanelStops(self, rows, method_hint):
        with self.assertRaises(ValueError, msg='summarize returned a summary instead of stopping the panel') as caught:
            PACKETS.summarize(manifest(), rows)
        message = str(caught.exception)
        self.assertIn('four-method panel cannot run', message)
        self.assertIn(method_hint, message)
        self.assertIn('blind plus context double reading', message)

    def test_fresh_separate_contexts_still_summarize(self):
        out = PACKETS.summarize(manifest(), reports())
        self.assertEqual(out['reported_methods'], list('ABCD'))

    def test_shared_context_stops_the_panel(self):
        rows = reports()
        rows[2]['context_isolation'] = 'shared'
        self.assertPanelStops(rows, 'C')

    def test_unknown_isolation_stops_the_panel(self):
        rows = reports()
        rows[0]['context_isolation'] = 'unknown'
        self.assertPanelStops(rows, 'A')

    def test_missing_context_id_stops_the_panel(self):
        rows = reports()
        rows[3]['context_id'] = 'unknown'
        self.assertPanelStops(rows, 'D')

    def test_reused_context_id_stops_the_panel(self):
        rows = reports()
        rows[1]['context_id'] = rows[0]['context_id']
        self.assertPanelStops(rows, 'A, B')

    def test_cli_exits_with_the_error_not_a_summary(self):
        import json, subprocess, sys, tempfile
        rows = reports()
        rows[1]['context_isolation'] = 'shared'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'manifest.json').write_text(json.dumps(manifest()), encoding='utf-8')
            paths = []
            for row in rows:
                path = folder / (row['method_id'] + '.json')
                path.write_text(json.dumps(row), encoding='utf-8')
                paths.append(str(path))
            run = subprocess.run([sys.executable, str(ROOT / 'skills/genealogy-read-manuscripts/scripts/method_packets.py'),
                                  'summarize', str(folder / 'manifest.json'), *paths], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, '')
        self.assertIn('four-method panel cannot run', run.stderr)

    def test_fallback_reading_cannot_carry_four_method_status(self):
        rows = reports()
        for row in rows:
            row['context_isolation'] = 'shared'
            row['context_id'] = 'CTX-ONE'
        with self.assertRaises(PACKETS.PanelUnavailable) as caught:
            PACKETS.summarize(manifest(), rows)
        error = caught.exception
        self.assertEqual(error.reading_label, 'double reading in one context')
        self.assertEqual(error.highest_confidence, 'tentative')
        self.assertIn('double reading in one context', str(error))
        self.assertNotIn('visually_supported', str(error))

    def test_skill_covers_hosts_without_fresh_contexts(self):
        skill = (ROOT / 'skills/genealogy-read-manuscripts/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('## Host without fresh contexts', skill)
        section = skill.split('## Host without fresh contexts', 1)[1].split('\n## ', 1)[0]
        for phrase in ('Stop the four-method panel', 'released packets', 'human reader',
                       'double reading in one context', 'highest confidence is tentative',
                       'Never report it as four-method agreement', 'context reading after a quick read'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_skill_tells_the_coordinator_to_stop_and_fall_back(self):
        skill = (ROOT / 'skills/genealogy-read-manuscripts/SKILL.md').read_text(encoding='utf-8')
        protocol = (ROOT / 'skills/genealogy-read-manuscripts/references/protocol.md').read_text(encoding='utf-8')
        for name, text in (('SKILL.md', skill), ('protocol.md', protocol)):
            with self.subTest(doc=name):
                self.assertTrue('blind plus context double reading' in text, name + ' lacks the fallback')
                self.assertFalse('non-isolated method passes' in text, name + ' still allows shared passes')
                self.assertFalse('Run bounded sequential method passes' in text, name + ' still allows shared passes')


if __name__ == '__main__':
    unittest.main(verbosity=2)
