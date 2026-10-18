#!/usr/bin/env python3
"""Layout checks: grader answer keys stay out of skills/, and the installer skips evaluation by default."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVALUATION = 'genealogy-evaluation'


def install_plan(*extra):
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, str(ROOT / 'install.py'), '--dest', str(Path(d) / 'skills'), *extra],
                           capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError('install.py failed: ' + (r.stdout + r.stderr).strip()[-300:])
    return [a['skill'] for a in json.loads(r.stdout)['actions']]


class EvaluationLayout(unittest.TestCase):
    def test_no_answer_keys_under_skills(self):
        hits = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'skills').rglob('*')
                      if 'benchmark' in p.parts and 'answer-keys' in p.parts)
        self.assertEqual(hits, [])

    def test_evaluation_skill_lives_outside_skills(self):
        self.assertFalse((ROOT / 'skills' / EVALUATION).exists())
        self.assertTrue((ROOT / 'evaluation' / EVALUATION / 'SKILL.md').is_file())

    def test_installer_excludes_evaluation_by_default(self):
        plan = install_plan()
        self.assertIn('genealogy-mode', plan)
        self.assertNotIn(EVALUATION, plan)

    def test_installer_includes_evaluation_with_flag(self):
        plan = install_plan('--include-evaluation')
        self.assertIn(EVALUATION, plan)
        self.assertEqual(len(plan), len(install_plan()) + 1)


if __name__ == '__main__':
    unittest.main()
