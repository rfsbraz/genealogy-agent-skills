#!/usr/bin/env python3
"""Tree gap finder: source registry format, candidate generation and registry learning. Fictional fixtures, no network."""
from pathlib import Path
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'genealogy-research-planner'
SCRIPT = SKILL / 'scripts' / 'gap_finder.py'
FIXTURES = ROOT / 'tests' / 'fixtures' / 'gap-finder'
REGISTRY = FIXTURES / 'registry'
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(ROOT / 'skills' / 'genealogy-mode' / 'scripts'))


def gap():
    import gap_finder
    return gap_finder


def case():
    return json.loads((FIXTURES / 'case.json').read_text(encoding='utf-8'))


def result(**kw):
    return gap().find_gaps(case(), gap().load_registry(kw.pop('registry', REGISTRY)), **kw)


def find(res, mode, kind, persons):
    return [c for c in res['candidates'] if c['mode'] == mode and c['kind'] == kind and sorted(c['person_ids']) == sorted(persons)]


def source_ids(candidate):
    return sorted(s['id'] for s in candidate['sources'])


class Registry(unittest.TestCase):
    def test_fixture_registry_is_valid(self):
        self.assertEqual(gap().validate_registry(json.loads((REGISTRY / 'XF.json').read_text(encoding='utf-8'))), [])

    def test_schema_and_validator_agree_on_the_fixture(self):
        from case_tools import check_shape
        schema = json.loads((SKILL / 'assets' / 'source-registry.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(check_shape(json.loads((REGISTRY / 'XF.json').read_text(encoding='utf-8')), schema, schema), [])

    def test_template_is_valid(self):
        template = json.loads((SKILL / 'assets' / 'source-registry-template.json').read_text(encoding='utf-8'))
        self.assertEqual(gap().validate_registry(template), [])

    def test_bad_entries_are_reported(self):
        data = json.loads((REGISTRY / 'XF.json').read_text(encoding='utf-8'))
        data['sources'][0]['access']['cost'] = 'cheap'
        data['sources'][1]['coverage'][0].update(from_year=1950, to_year=1900)
        data['sources'][2]['id'] = data['sources'][0]['id']
        data['sources'][2]['record_types'] = []
        errors = ' | '.join(gap().validate_registry(data))
        for expected in ('cost', 'from_year', 'duplicate', 'record_types'):
            self.assertIn(expected, errors)

    def test_cli_validates_a_folder(self):
        run = subprocess.run([sys.executable, str(SCRIPT), 'validate-registry', str(REGISTRY)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


class DetailMode(unittest.TestCase):
    def setUp(self):
        self.res = result()

    def test_a_failed_search_is_not_suggested_again(self):
        for c in self.res['candidates']:
            # Ana's own baptism; the children search reads the same books for other entries.
            if c['person_ids'] == ['P-ANA']:
                for s in c['sources']:
                    self.assertFalse(s['id'] == 'XF-PARISH' and 'baptism' in s['record_types'], c['id'])
        skipped = [s for s in self.res['skipped'] if s['kind'] == 'birth' and s['person_ids'] == ['P-ANA']]
        self.assertEqual(len(skipped), 1)
        self.assertIn('SEARCH-ANA-BAPT', skipped[0]['reason'])

    def test_unsourced_death_points_at_sources_that_match_place_period_and_type(self):
        [death] = find(self.res, 'detail', 'death', ['P-ANA'])
        self.assertEqual(source_ids(death), ['XF-CIVIL', 'XF-PARISH'])
        civil = next(s for s in death['sources'] if s['id'] == 'XF-CIVIL')
        self.assertTrue(civil['needs_approval'])
        self.assertIn('1911', civil['why'])
        self.assertTrue(death['needs_approval'])

    def test_place_limited_sources_and_earlier_attempts(self):
        [death] = find(self.res, 'detail', 'death', ['P-RUI'])
        self.assertEqual(source_ids(death), ['XF-CIVIL', 'XF-NEWS'])
        news = next(s for s in death['sources'] if s['id'] == 'XF-NEWS')
        self.assertEqual([a['search_id'] for a in news['earlier_attempts']], ['SEARCH-RUI-DEATH'])

    def test_missing_marriage_for_a_couple(self):
        [marriage] = find(self.res, 'detail', 'marriage', ['P-ANA', 'P-RUI'])
        self.assertEqual(source_ids(marriage), ['XF-PARISH'])
        self.assertEqual(marriage['years'], [1889, 1905])

    def test_a_sourced_fact_is_not_a_gap(self):
        self.assertEqual(find(self.res, 'detail', 'birth', ['P-LUIS']), [])
        self.assertEqual(find(self.res, 'detail', 'birth', ['P-RUI'])[0]['sources'][0]['id'], 'XF-PARISH')


class ExpandMode(unittest.TestCase):
    def setUp(self):
        self.res = result()

    def test_people_without_parents_get_a_parents_search(self):
        [parents] = find(self.res, 'expand', 'parents', ['P-ANA'])
        self.assertEqual([(s['id'], s['record_types']) for s in parents['sources']], [('XF-PARISH', ['marriage'])])
        self.assertEqual(find(self.res, 'expand', 'parents', ['P-LUIS']), [])

    def test_couples_get_a_children_search_over_their_fertile_years(self):
        [children] = find(self.res, 'expand', 'children', ['P-ANA', 'P-RUI'])
        self.assertEqual(children['years'], [1890, 1924])
        self.assertEqual(children['known_children'], ['P-LUIS'])
        self.assertEqual(source_ids(children), ['XF-CIVIL', 'XF-PARISH'])

    def test_candidates_are_ranked_and_filterable(self):
        scores = [c['priority'] for c in self.res['candidates']]
        self.assertEqual(scores, sorted(scores, reverse=True))
        only = result(person_ids=['P-RUI'], modes=('detail',))
        self.assertTrue(only['candidates'])
        self.assertTrue(all('P-RUI' in c['person_ids'] and c['mode'] == 'detail' for c in only['candidates']))

    def test_output_is_stable(self):
        self.assertEqual(result(), result())


class Learning(unittest.TestCase):
    def test_a_recorded_coverage_gap_is_learned_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / 'registry'
            shutil.copytree(REGISTRY, registry)
            cmd = [sys.executable, str(SCRIPT), 'learn', str(FIXTURES / 'case.json'), '--registry', str(registry),
                   '--search', 'SEARCH-COUPLE-MARR']
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            data = json.loads((registry / 'XF.json').read_text(encoding='utf-8'))
            learned = [g for g in data['sources'][0]['known_gaps'] if g.get('learned_from') == 'SEARCH-COUPLE-MARR']
            self.assertEqual(len(learned), 1)
            self.assertEqual(gap().validate_registry(data), [])
            again = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(again.returncode, 0)
            self.assertIn('already', again.stdout)
            res = result(registry=registry)
            self.assertEqual(find(res, 'detail', 'marriage', ['P-ANA', 'P-RUI']), [])
            self.assertTrue(any(s['kind'] == 'marriage' and 'missing online' in s['reason'] for s in res['skipped']))

    def test_a_search_without_a_recorded_gap_teaches_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / 'registry'
            shutil.copytree(REGISTRY, registry)
            before = (registry / 'XF.json').read_text(encoding='utf-8')
            run = subprocess.run([sys.executable, str(SCRIPT), 'learn', str(FIXTURES / 'case.json'), '--registry',
                                  str(registry), '--search', 'SEARCH-ANA-BAPT'], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual((registry / 'XF.json').read_text(encoding='utf-8'), before)


class Cli(unittest.TestCase):
    def test_json_output(self):
        run = subprocess.run([sys.executable, str(SCRIPT), 'gaps', str(FIXTURES / 'case.json'), '--registry', str(REGISTRY),
                              '--json'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)
        self.assertTrue(data['candidates'])
        self.assertIn('scope', data)

    def test_text_output_flags_paid_sources(self):
        run = subprocess.run([sys.executable, str(SCRIPT), 'gaps', str(FIXTURES / 'case.json'), '--registry', str(REGISTRY)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('ask before ordering', run.stdout)


class FixturesAreFictional(unittest.TestCase):
    def test_registry_and_case_say_they_are_synthetic(self):
        self.assertIn('Fictional', (REGISTRY / 'XF.json').read_text(encoding='utf-8'))
        self.assertTrue(case()['case_id'].startswith('C-GAP-FIXTURE'))


class Docs(unittest.TestCase):
    def test_planner_and_reference_describe_the_helper(self):
        skill = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('scripts/gap_finder.py', skill)
        self.assertIn('references/source-registry.md', skill)
        ref = (SKILL / 'references' / 'source-registry.md').read_text(encoding='utf-8')
        for word in ('known_gaps', 'needs_approval', 'learn', 'detail', 'expand'):
            self.assertIn(word, ref)


if __name__ == '__main__':
    unittest.main(verbosity=2)
