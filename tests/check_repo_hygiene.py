#!/usr/bin/env python3
"""Repository hygiene: test docstrings, the answer keys folder and the documented skill count."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Hygiene(unittest.TestCase):
    OLD_KEYS = 'benchmark/' + 'private'

    def test_test_docstrings_do_not_cite_issue_numbers(self):
        # Issue numbers restart when the repository is recreated; describe the behaviour instead.
        hits = [p.name for p in sorted((ROOT / 'tests').glob('check_*.py'))
                if re.search(r'Issue[ ]#|\(#\d+\)', p.read_text(encoding='utf-8'))]
        self.assertEqual(hits, [])

    def test_answer_keys_folder_and_no_old_path(self):
        keys = ROOT / 'evaluation/genealogy-evaluation/assets/benchmark/answer-keys'
        self.assertTrue(keys.is_dir() and list(keys.glob('*.json')))
        out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout
        hits = []
        for rel in [p for p in out.decode().split('\0') if p]:
            path = ROOT / rel
            if path.is_file() and path.suffix in ('.py', '.md', '.json', '.yml', '.yaml', '.txt', '') :
                if self.OLD_KEYS in path.read_text(encoding='utf-8', errors='ignore') or self.OLD_KEYS in rel:
                    hits.append(rel)
        self.assertEqual(hits, [])

    def test_validation_history_counts_real_skills(self):
        count = len(list(ROOT.glob('skills/*/SKILL.md'))) + len(list(ROOT.glob('evaluation/*/SKILL.md')))
        # The newest history entry states the current count; older sections keep their own numbers.
        found = re.findall(r'All (\d+) skill entrypoints passed', (ROOT / 'docs/VALIDATION.md').read_text(encoding='utf-8'))
        self.assertEqual(found[:1], [str(count)])



if __name__ == '__main__':
    unittest.main()
