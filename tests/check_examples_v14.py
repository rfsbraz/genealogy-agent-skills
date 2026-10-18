#!/usr/bin/env python3
"""The synthetic v1.4 example reproduces: reread, then project, gives the shipped files."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / 'examples/v1.4'
CLI = [sys.executable, str(ROOT / 'genealogy.py')]


def run(*args):
    out = subprocess.run(CLI + list(args), capture_output=True, text=True, cwd=ROOT)
    if out.returncode:
        raise AssertionError(out.stdout + out.stderr)
    return out.stdout


def strip_time(case):
    for change in case.get('changes', []):
        change.pop('recorded_at', None)
    return case


class ExampleV14(unittest.TestCase):
    def test_reread_matches_shipped_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / 'case.json'
            shutil.copy(EX / 'case-before.json', case)
            run('reread', str(case), '--old', 'O1', '--reading', str(EX / 'replacement.json'),
                '--reason', 'Synthetic clearer final digit.', '--actor', 'synthetic-test', '--expected-revision', '0')
            got = strip_time(json.loads(case.read_text(encoding='utf-8')))
            want = strip_time(json.loads((EX / 'case-after-reread.json').read_text(encoding='utf-8')))
            self.assertEqual(got, want)
            run('check', str(case))

    def test_projection_matches_shipped_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'build'
            run('project', str(EX / 'case-after-reread.json'), '--mapping', str(EX / 'repository-map.json'),
                '--tree', str(EX / 'existing-tree.json'), '--out', str(out))
            shipped = sorted(p.relative_to(EX / 'generated').as_posix() for p in (EX / 'generated').rglob('*') if p.is_file())
            built = sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file())
            self.assertEqual(built, shipped)
            for rel in shipped:
                with self.subTest(file=rel):
                    self.assertEqual(json.loads((out / rel).read_text(encoding='utf-8')),
                                     json.loads((EX / 'generated' / rel).read_text(encoding='utf-8')))

    def test_manual_tree_note_survives(self):
        tree = json.loads((EX / 'generated/data/tree.json').read_text(encoding='utf-8'))
        before = json.loads((EX / 'existing-tree.json').read_text(encoding='utf-8'))
        manual = [n for p in before['people'] for n in p.get('notes', [])]
        kept = [n for p in tree['people'] for n in p.get('notes', [])]
        self.assertTrue(manual)
        self.assertEqual(kept, manual)

    def test_example_is_labelled_synthetic_and_has_relative_paths(self):
        for path in EX.rglob('*'):
            if path.is_file() and path.suffix in ('.json', '.md'):
                text = path.read_text(encoding='utf-8')
                with self.subTest(file=path.name):
                    self.assertNotRegex(text, r'(?m)(^|[\s"])/(workspace|home|Users|tmp)/')
        self.assertIn('synthetic', (EX / 'WORKFLOW.md').read_text(encoding='utf-8').lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
