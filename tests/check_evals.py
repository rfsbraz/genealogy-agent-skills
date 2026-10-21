#!/usr/bin/env python3
"""Offline checks for the claude plugin eval suites under evals/.

Nothing here calls a model. The tests check the case files against the
documented plugin-eval format, keep the quality cases in sync with the
synthetic benchmark, and run every regex grader in Python against a correct
and a deliberately wrong result.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import build_evals as B  # noqa: E402

EVALS = ROOT / 'evals'
BENCH = ROOT / 'evaluation' / 'genealogy-evaluation' / 'assets' / 'benchmark'
PROMPT_KEYS = {'schema_version', 'name', 'description', 'tags', 'plugins', 'runs', 'expected_outcome',
               'model', 'max_turns', 'timeout_seconds', 'allowed_tools', 'append_system_prompt', 'env'}
GRADER_KEYS = {'type', 'weight', 'arm', 'pattern', 'flags', 'match', 'target', 'tool', 'input_match',
               'min', 'max', 'before', 'after', 'path', 'exists', 'criteria', 'focus', 'baseline_file'}
GRADER_TYPES = {'regex', 'tool_used', 'tool_order', 'file_exists', 'llm', 'baseline'}
AUTO = {'genealogy-mode', 'genealogy-interview', 'genealogy-narrative'}


def cases(prefix=''):
    return sorted(p.parent for p in EVALS.glob(prefix + '*/prompt.md'))


def skill_names():
    return {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}


class Format(unittest.TestCase):
    def test_suite_exists(self):
        self.assertTrue(EVALS.is_dir())
        self.assertGreaterEqual(len(cases()), 30)

    def test_prompt_frontmatter(self):
        for case in cases():
            meta, body = B.read_frontmatter((case / 'prompt.md').read_text(encoding='utf-8'))
            with self.subTest(case=case.name):
                self.assertLessEqual(set(meta), PROMPT_KEYS)
                self.assertTrue(body.strip())
                self.assertIsInstance(meta['tags'], list)
                self.assertTrue({'trigger', 'quality'} & set(meta['tags']))
                self.assertLessEqual(int(meta['max_turns']), 12)
                self.assertNotIn('Bash', meta.get('allowed_tools', []))
                self.assertNotIn('env', meta)

    def test_graders(self):
        names = skill_names()
        for case in cases():
            graders = sorted((case / 'graders').glob('*.md'))
            with self.subTest(case=case.name):
                self.assertTrue(graders)
                for g in graders:
                    meta, _ = B.read_frontmatter(g.read_text(encoding='utf-8'))
                    self.assertLessEqual(set(meta), GRADER_KEYS, g)
                    self.assertIn(meta['type'], GRADER_TYPES, g)
                    self.assertNotEqual(meta['type'], 'llm', 'paid judge graders are opt-in; keep the suite deterministic')
                    for key in ('pattern', 'input_match'):
                        if key in meta:
                            re.compile(meta[key])
                    for name in re.findall(r'genealogy-[a-z-]+', meta.get('input_match', '')):
                        self.assertIn(name, names, g)

    def test_no_secrets_or_paid_ci(self):
        for path in EVALS.rglob('*'):
            if path.is_file() and 'results' not in path.relative_to(EVALS).parts:
                self.assertNotRegex(path.read_text(encoding='utf-8'), r'(?i)api[_-]?key|sk-ant-')
        for wf in (ROOT / '.github' / 'workflows').glob('*.yml'):
            text = wf.read_text(encoding='utf-8')
            self.assertNotIn('plugin eval', text, wf)
            self.assertNotIn('ANTHROPIC', text, wf)


class Triggers(unittest.TestCase):
    def load(self):
        out = {}
        for case in cases('trigger-'):
            meta, _ = B.read_frontmatter((case / 'prompt.md').read_text(encoding='utf-8'))
            graders = {g.stem: B.read_frontmatter(g.read_text(encoding='utf-8'))[0]
                       for g in (case / 'graders').glob('*.md')}
            out[case.name] = (meta, graders)
        return out

    def test_mix(self):
        loaded = self.load()
        should = [n for n, (m, _) in loaded.items() if 'should-trigger' in m['tags']]
        near = [n for n, (m, _) in loaded.items() if 'near-miss' in m['tags']]
        self.assertGreaterEqual(len(should), 8)
        self.assertGreaterEqual(len(near), 8)
        self.assertEqual(len(should) + len(near), len(loaded))
        fired = {g['input_match'] for n in should for k, g in loaded[n][1].items() if k == 'fires'}
        for name in AUTO:
            self.assertTrue(any(name in pattern for pattern in fired), name)

    def test_every_case_guards_specialists(self):
        specialists = skill_names() - AUTO
        for name, (meta, graders) in self.load().items():
            with self.subTest(case=name):
                g = graders['no-specialist-skill']
                self.assertEqual((g['type'], g['tool'], g['min'], g['max'], g['arm']), ('tool_used', 'Skill', 0, 0, 'both'))
                rx = re.compile(g['input_match'])
                for s in specialists:
                    self.assertTrue(rx.search('{"skill": "genealogy:%s"}' % s), s)
                for s in AUTO:
                    self.assertFalse(rx.search('{"skill": "genealogy:%s"}' % s), s)

    def test_near_miss_forbids_auto_skills(self):
        for name, (meta, graders) in self.load().items():
            if 'near-miss' not in meta['tags']:
                continue
            with self.subTest(case=name):
                g = graders['does-not-fire']
                self.assertEqual((g['min'], g['max'], g['arm']), (0, 0, 'both'))
                rx = re.compile(g['input_match'])
                for s in AUTO:
                    self.assertTrue(rx.search('{"skill":"%s"}' % s))

    def test_should_trigger_matches_only_its_skill(self):
        for name, (meta, graders) in self.load().items():
            if 'should-trigger' not in meta['tags']:
                continue
            with self.subTest(case=name):
                rx = re.compile(graders['fires']['input_match'])
                hits = [s for s in AUTO if rx.search('{"skill": "genealogy:%s"}' % s)]
                self.assertEqual(len(hits), 1)


class Quality(unittest.TestCase):
    def test_in_sync_with_benchmark(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_evals.py'), '--check'],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_one_case_per_benchmark_case(self):
        bench = {json.loads(p.read_text())['case_id'] for p in (BENCH / 'answer-keys').glob('*.json')}
        self.assertEqual({p.name for p in cases('quality-')}, {'quality-' + b for b in bench})

    def test_answer_keys_stay_out_of_prompts(self):
        for case in cases('quality-'):
            text = (case / 'prompt.md').read_text(encoding='utf-8')
            self.assertNotIn('answer-key', text)
            self.assertNotIn('assertions', text)

    def test_graders_pass_correct_and_fail_wrong_results(self):
        for key in sorted((BENCH / 'answer-keys').glob('*.json')):
            gold = json.loads(key.read_text(encoding='utf-8'))
            case = EVALS / ('quality-' + gold['case_id'])
            graders = {g.stem: B.read_frontmatter(g.read_text(encoding='utf-8'))[0]
                       for g in (case / 'graders').glob('*.md')}
            good = B.reference_result(gold)
            with self.subTest(case=gold['case_id'], result='good'):
                self.assertEqual(B.failed_regex_graders(graders, json.dumps(good, indent=2)), [])
                self.assertEqual(B.failed_regex_graders(graders, json.dumps(good)), [])
            bad = B.wrong_result(gold)
            failed = B.failed_regex_graders(graders, json.dumps(bad, indent=2))
            critical = [a['path'].rsplit('/', 1)[1] for a in gold['assertions'] if a['critical']]
            with self.subTest(case=gold['case_id'], result='wrong'):
                for field in critical:
                    self.assertIn('decision-' + field.replace('_', '-'), failed)
            fenced = 'Here it is:\n```json\n' + json.dumps(good) + '\n```'
            with self.subTest(case=gold['case_id'], result='fenced'):
                self.assertIn('bare-json', B.failed_regex_graders(graders, fenced))

    def test_critical_assertions_weigh_more(self):
        for key in sorted((BENCH / 'answer-keys').glob('*.json')):
            gold = json.loads(key.read_text(encoding='utf-8'))
            case = EVALS / ('quality-' + gold['case_id'])
            for a in gold['assertions']:
                name = 'decision-' + a['path'].rsplit('/', 1)[1].replace('_', '-')
                meta, _ = B.read_frontmatter((case / 'graders' / (name + '.md')).read_text(encoding='utf-8'))
                self.assertEqual(meta['weight'], 3 if a['critical'] else 1, name)


if __name__ == '__main__':
    unittest.main(verbosity=1)
