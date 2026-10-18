#!/usr/bin/env python3
"""Synthetic regression checks for review controls and offline discovery helpers."""
import copy
from datetime import date
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/genealogy-mode/scripts'))
from case_tools import validate_case
from gps_review import evidence_digest

spec = importlib.util.spec_from_file_location('country_tools', ROOT / 'skills/genealogy-origin-source-discovery/scripts/country_tools.py')
COUNTRY = importlib.util.module_from_spec(spec); spec.loader.exec_module(COUNTRY)


def reviewed_case():
    case = json.loads((ROOT / 'skills/genealogy-mode/assets/case-template.json').read_text())
    case['sources'] = [{'id': 'S1', 'title': 'Synthetic register, fixture only', 'source_type': 'original', 'derived_from': []}]
    case['citations'] = [{'id': 'C1', 'source_id': 'S1', 'locator': 'p. 1, entry 4', 'text': 'Synthetic Archive, register TEST, p. 1, entry 4; supplied fixture image.'}]
    case['observations'] = [{'id': 'O1', 'source_id': 'S1', 'citation_id': 'C1', 'locator': 'p. 1, entry 4', 'statement': 'Synthetic event statement.', 'uncertainty': 'Fixture text is supplied; no image reading tested.'}]
    case['searches'] = [{'id': 'SR1', 'question_id': 'Q-1', 'target': 'Synthetic collection', 'method': 'Supplied fixture review', 'coverage': 'All supplied fixture material, p. 1', 'outcome': 'found'}]
    conclusion = {'id': 'K1', 'question_id': 'Q-1', 'claim': 'Synthetic claim for validator testing only.', 'status': 'supported', 'observation_ids': ['O1'], 'rationale': 'Synthetic reviewer judgment; not a real genealogy conclusion.', 'depends_on': []}
    case['conclusions'] = [conclusion]
    conclusion['gps_review'] = {
        'version': '1.0', 'decision': 'ready', 'evidence_digest': evidence_digest(case),
        'reviewer': {'id': 'synthetic-test-reviewer', 'kind': 'agent'}, 'reviewed_on': '2026-10-17',
        'research': {'status': 'met', 'summary': 'All synthetic fixture avenues assessed.', 'search_ids': ['SR1'], 'coverage': [{'record_family': 'synthetic', 'jurisdiction': 'fictional', 'period': 'fixture period', 'disposition': 'searched', 'material': True, 'search_ids': ['SR1'], 'rationale': 'All supplied fixture material inspected.'}], 'remaining_gaps': []},
        'citations': {'status': 'met', 'summary': 'Fixture locator checked.', 'citation_ids': ['C1']},
        'analysis': {'status': 'met', 'summary': 'Synthetic test reasoning only.', 'observation_ids': ['O1'], 'hypothesis_ids': [],
                     'source_assessments': [{'source_id': 'S1', 'form': 'original', 'informant_assessment': 'Synthetic informant.', 'independence_group': 'S1', 'rationale': 'One supplied source.'}],
                     'information_assessments': [{'observation_id': 'O1', 'information_quality': 'primary', 'evidence_relevance': 'direct', 'rationale': 'Explicit synthetic statement.'}]},
        'conflicts': {'status': 'met', 'summary': 'No conflicts in supplied synthetic fixture.', 'items': []},
        'writing': {'status': 'met', 'summary': 'Synthetic reasoning recorded.', 'form': 'statement', 'text': 'This fixture exercises validation, not historical accuracy.', 'reopen_when': 'Any new source or corrected observation.'}}
    return case


class GPSChecks(unittest.TestCase):
    def test_complete_review_record(self):
        self.assertEqual(validate_case(reviewed_case()), [])

    def test_all_five_elements_required(self):
        for element in ('research', 'citations', 'analysis', 'conflicts', 'writing'):
            case = reviewed_case(); case['conclusions'][0]['gps_review'][element]['status'] = 'open'
            self.assertTrue(validate_case(case), element)

    def test_new_case_blocks_unreviewed_acceptance(self):
        case = reviewed_case(); del case['conclusions'][0]['gps_review']
        self.assertTrue(validate_case(case))

    def test_working_lead_can_be_saved(self):
        case = reviewed_case(); case['conclusions'][0]['status'] = 'provisional'; del case['conclusions'][0]['gps_review']
        self.assertEqual(validate_case(case), [])

    def test_legacy_is_readable_but_strict_check_flags_review(self):
        case = reviewed_case(); case['schema_version'] = '1.0'; del case['conclusions'][0]['gps_review']
        self.assertEqual(validate_case(case), [])
        self.assertTrue(validate_case(case, gps=True))

    def test_changed_source_invalidates_review(self):
        case = reviewed_case(); case['sources'][0]['title'] = 'Corrected source'
        self.assertTrue(any('stale' in e for e in validate_case(case)))

    def test_checkpoint_does_not_invalidate_review(self):
        case = reviewed_case(); case['revision'] += 1; case['checkpoint']['next_action'] = 'Resume tomorrow'
        self.assertEqual(validate_case(case), [])

    def test_material_conflict_blocks(self):
        case = reviewed_case(); review = case['conclusions'][0]['gps_review']
        review['conflicts']['items'] = [{'description': 'Conflicting parent name', 'observation_ids': ['O1'], 'material': True, 'status': 'open', 'rationale': 'Not yet resolved.'}]
        self.assertTrue(any('material conflict' in e for e in validate_case(case)))

    def test_material_gap_blocks(self):
        case = reviewed_case(); case['conclusions'][0]['gps_review']['research']['remaining_gaps'] = [{'description': 'Decisive unread page', 'material': True, 'next_action': 'Read the page.'}]
        self.assertTrue(any('material evidence gaps' in e for e in validate_case(case)))

    def test_partial_search_cannot_count_as_complete(self):
        case = reviewed_case(); case['searches'][0]['outcome'] = 'partial'
        case['conclusions'][0]['gps_review']['evidence_digest'] = evidence_digest(case)
        self.assertTrue(any('incomplete search' in e for e in validate_case(case)))

    def test_missing_full_citation_blocks(self):
        case = reviewed_case(); del case['citations'][0]['text']
        case['conclusions'][0]['gps_review']['evidence_digest'] = evidence_digest(case)
        self.assertTrue(any('full citation text' in e for e in validate_case(case)))

    def test_missing_information_assessment_blocks(self):
        case = reviewed_case(); case['conclusions'][0]['gps_review']['analysis']['information_assessments'] = []
        self.assertTrue(validate_case(case))

    def test_negative_evidence_requires_basis(self):
        case = reviewed_case(); case['conclusions'][0]['gps_review']['analysis']['information_assessments'][0]['evidence_relevance'] = 'negative'
        self.assertTrue(any('negative evidence' in e for e in validate_case(case)))

    def test_recorded_alternative_cannot_be_omitted(self):
        case = reviewed_case(); case['hypotheses'] = [{'id': 'H1', 'question_id': 'Q-1', 'explanation': 'Another identity', 'status': 'provisional', 'support_ids': [], 'counterevidence_ids': ['O1']}]
        case['conclusions'][0]['gps_review']['evidence_digest'] = evidence_digest(case)
        self.assertTrue(any('omits recorded alternatives' in e for e in validate_case(case)))

    def test_unknown_review_field_rejected(self):
        case = reviewed_case(); case['conclusions'][0]['gps_review']['ignore_conflicts'] = True
        self.assertTrue(any('unexpected property' in e for e in validate_case(case)))

    def test_whitespace_is_not_reasoning(self):
        case = reviewed_case(); case['conclusions'][0]['gps_review']['writing']['text'] = '  '
        self.assertTrue(validate_case(case))


class CountryChecks(unittest.TestCase):
    def test_catalogue_integrity(self):
        self.assertEqual(COUNTRY.validate(), [])
        self.assertEqual(len(COUNTRY.index()['countries']), 14)

    def test_alias_and_accent_lookup(self):
        self.assertEqual(COUNTRY.lookup('México')['code'], 'MX')
        self.assertEqual(COUNTRY.lookup('UK')['code'], 'GB')

    def test_portugal_roles(self):
        entries = {s['id']: s for s in COUNTRY.lookup('PT')['sources']}
        self.assertEqual(entries['PT-CRAV']['kind'], 'request_service')
        self.assertEqual(entries['PT-DIGITARQ']['kind'], 'catalogue')
        self.assertEqual(entries['PT-ANTT']['kind'], 'repository')
        self.assertEqual(entries['PT-IRN']['kind'], 'civil_authority')

    def test_unknown_country_continues_discovery(self):
        result = COUNTRY.plan('Angola', place='Luanda')
        self.assertEqual(result['status'], 'discovery_required')
        self.assertEqual(result['sources'], [])
        self.assertGreater(len(result['next_steps']), 0)

    def test_country_input_is_not_a_file_path(self):
        self.assertIsNone(COUNTRY.lookup('../../case'))

    def test_default_shortlist_and_unverified_coverage(self):
        result = COUNTRY.plan('Portugal')
        self.assertEqual(len(result['sources']), 3)
        self.assertTrue(all(s['coverage_status'] == 'not_assessed_for_person' for s in result['sources']))

    def test_old_entry_and_notice_prompt_refresh(self):
        self.assertTrue(all(s['refresh_due'] for s in COUNTRY.plan('Portugal', today=date(2027, 10, 17))['sources']))
        self.assertTrue(COUNTRY.plan('Brazil')['sources'][1]['refresh_due'])


class FrontDoorChecks(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'genealogy.py'), *args], capture_output=True, text=True)

    def test_start_status_check_and_resume_data_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / 'case.json')
            self.assertEqual(self.run_cli('start', '--question', 'Who were Ana’s parents?', '--out', target).returncode, 0)
            before = Path(target).read_bytes()
            result = self.run_cli('status', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no conclusion recorded', result.stdout)
            self.assertEqual(self.run_cli('check', target).returncode, 0)
            self.assertEqual(Path(target).read_bytes(), before)
            self.assertEqual(self.run_cli('start', '--question', 'Overwrite?', '--out', target).returncode, 2)

    def test_country_leads_and_fallback(self):
        self.assertIn('Digitarq', self.run_cli('sources', 'Portugal').stdout)
        self.assertIn('No starter profile yet', self.run_cli('sources', 'Angola').stdout)


class SourceFilterChecks(unittest.TestCase):
    """Sources filters either change the result or say plainly what they do."""
    FAMILIES = ['civil', 'household', 'institutional', 'legal', 'migration', 'military', 'press', 'religious']

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'genealogy.py'), *args], capture_output=True, text=True)

    def test_record_family_vocabulary_is_closed(self):
        self.assertEqual(sorted(COUNTRY.RECORD_FAMILIES), self.FAMILIES)
        with tempfile.TemporaryDirectory() as tmp:
            import shutil
            database = Path(tmp) / 'countries'; shutil.copytree(COUNTRY.DATABASE, database)
            profile = json.loads((database / 'PT.json').read_text(encoding='utf-8'))
            profile['sources'][0]['record_families'].append('surnames')
            (database / 'PT.json').write_text(json.dumps(profile), encoding='utf-8')
            self.assertTrue(any('surnames' in e for e in COUNTRY.validate(database)))

    def test_surname_as_family_is_rejected_with_valid_values(self):
        with self.assertRaises(ValueError) as caught: COUNTRY.plan('Portugal', family='Exampleson')
        for family in self.FAMILIES: self.assertIn(family, str(caught.exception))
        result = self.run_cli('sources', 'Portugal', '--family', 'Exampleson')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('record family', result.stderr); self.assertIn('religious', result.stderr)

    def test_text_output_shows_scope_and_filled_queries(self):
        out = self.run_cli('sources', 'Portugal', '--place', 'Vila Exemplo', '--period', '1850').stdout
        self.assertIn('Scope:', out); self.assertIn('Search queries:', out)
        self.assertTrue(any('Vila Exemplo' in line and '1850' in line for line in out.splitlines()), out)
        self.assertIn('do not filter', out)
        plain = self.run_cli('sources', 'Portugal').stdout
        self.assertNotIn('do not filter', plain)

    def test_family_without_effect_says_so(self):
        every = COUNTRY.plan('Portugal', family='civil')
        self.assertTrue(any('civil' in n and 'no effect' in n for n in every['notes']), every['notes'])
        none = COUNTRY.plan('Portugal', family='military')
        self.assertTrue(any('military' in n and 'no effect' in n for n in none['notes']), none['notes'])
        useful = COUNTRY.plan('Portugal', family='migration')
        self.assertEqual(useful['sources'][0]['id'], 'PT-DIGITARQ')
        self.assertFalse(any('no effect' in n for n in useful['notes']))
        self.assertIn('no effect', self.run_cli('sources', 'Portugal', '--family', 'military').stdout)

    def test_unknown_country_text_shows_queries(self):
        out = self.run_cli('sources', 'Angola', '--place', 'Vila Exemplo').stdout
        self.assertIn('Search queries:', out); self.assertIn('Vila Exemplo', out)

    def test_help_explains_filters(self):
        out = self.run_cli('sources', '--help').stdout
        self.assertIn('not a surname', out); self.assertIn('migration', out); self.assertIn('search queries', out)


if __name__ == '__main__':
    unittest.main(verbosity=2)
