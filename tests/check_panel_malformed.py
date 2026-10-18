#!/usr/bin/env python3
"""Malformed packet input and reports fail with a structured error; whitespace is not a reading.

Ported from the v1.4.2 review fixes. Deterministic: synthetic dictionaries only, no model calls.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_v141 import MODULE, inputs, manifest, reports  # noqa: E402


class MalformedInput(unittest.TestCase):
    def test_whitespace_does_not_count_as_literal_agreement(self):
        rows = reports()
        for row in rows:
            row['spans'][0]['reading'] = '  '
        out = MODULE.summarize(manifest(), rows)['agreement']['R1']
        self.assertEqual(out['candidate_groups'], [])
        self.assertEqual(out['methods_without_literal'], list('ABCD'))

    def test_malformed_report_members_fail_cleanly(self):
        rows = reports(); rows[0]['spans'] = [None]
        with self.assertRaisesRegex(ValueError, 'spans'):
            MODULE.summarize(manifest(), rows)
        rows = reports(); rows[0]['spans'][0]['method_product'] = 'not an object'
        with self.assertRaisesRegex(ValueError, 'method_product'):
            MODULE.summarize(manifest(), rows)

    def test_non_object_reports_fail_cleanly(self):
        with self.assertRaisesRegex(ValueError, 'Reports'):
            MODULE.summarize(manifest(), {'A': reports()[0]})
        with self.assertRaisesRegex(ValueError, 'report'):
            MODULE.summarize(manifest(), [None])

    def test_malformed_targets_and_clues_fail_with_value_error(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            spec = inputs(p); spec['targets'] = [None]
            with self.assertRaisesRegex(ValueError, 'targets'):
                MODULE.build(spec, p, p / 'packets')
            spec = inputs(p); spec['verified_context']['clues'] = [None]
            with self.assertRaisesRegex(ValueError, 'clue'):
                MODULE.build(spec, p, p / 'packets')
            self.assertFalse((p / 'packets').exists())

    def test_malformed_input_returns_json_error_in_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory); bad = p / 'bad.json'
            bad.write_text(json.dumps({'source_id': 'S', 'targets': [None]}))
            run = subprocess.run([sys.executable, MODULE.__file__, 'build', str(bad), '--out', str(p / 'packets')],
                                 capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('error', json.loads(run.stderr))
        self.assertNotIn('Traceback', run.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
