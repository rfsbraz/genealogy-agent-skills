#!/usr/bin/env python3
"""GEDCOM pre-import check and import into a provisional case. Synthetic fixtures, no network."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills' / 'genealogy-mode' / 'scripts'
FIXTURES = ROOT / 'tests' / 'fixtures' / 'gedcom'
sys.path.insert(0, str(SCRIPTS))


def tools():
    import gedcom_tools
    return gedcom_tools


def kinds(report):
    return sorted((i['kind'], tuple(i['records'])) for i in report['issues'])


class Parsing(unittest.TestCase):
    def test_records_levels_and_continuations(self):
        tree = tools().parse_gedcom(FIXTURES / 'clean.ged')
        self.assertEqual(sorted(tree['individuals']), ['@I1@', '@I2@', '@I3@', '@I4@'])
        self.assertEqual(tree['individuals']['@I1@']['name'], 'Tomé Fictício')
        self.assertEqual(tree['individuals']['@I4@']['notes'], ["Tree owner's note: said to have\nemigrated."])
        family = tree['families']['@F1@']
        self.assertEqual((family['husband'], family['wife'], family['children']), ('@I1@', '@I2@', ['@I3@', '@I4@']))
        birth = tree['individuals']['@I1@']['events'][0]
        self.assertEqual(birth['tag'], 'BIRT')
        self.assertEqual(birth['place'], 'Vila Inventada, Distrito Exemplo')
        self.assertEqual(birth['sources'], [{'source': '@S1@', 'page': 'Livro 1, folha 2'}])
        self.assertEqual(tree['sources']['@S1@']['title'], 'Registo paroquial sintético de Vila Inventada')
        self.assertEqual(tree['version'], '5.5.1')

    def test_byte_order_mark_and_crlf_are_accepted(self):
        text = (FIXTURES / 'clean.ged').read_text(encoding='utf-8').replace('\n', '\r\n')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bom.ged'
            path.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
            self.assertEqual(len(tools().parse_gedcom(path)['individuals']), 4)

    def test_malformed_line_is_reported_with_its_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.ged'
            path.write_text('0 HEAD\nnot a gedcom line\n0 TRLR\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'line 2'):
                tools().parse_gedcom(path)


class Dates(unittest.TestCase):
    def test_date_forms_keep_the_literal_and_a_range(self):
        parse = tools().parse_date
        cases = {
            '3 MAR 1910': ('exact', '1910-03-03', '1910-03-03'),
            'MAR 1883': ('month', '1883-03', '1883-03'),
            '1878': ('year', '1878', '1878'),
            'ABT 1850': ('approximate', '1850', '1850'),
            'BET 1852 AND 1854': ('range', '1852', '1854'),
            'BEF 1900': ('before', None, '1900'),
            'AFT 1900': ('after', '1900', None),
        }
        for literal, (kind, earliest, latest) in cases.items():
            with self.subTest(literal=literal):
                value = parse(literal)
                self.assertEqual(value['literal'], literal)
                self.assertEqual((value['kind'], value['earliest'], value['latest']), (kind, earliest, latest))

    def test_impossible_and_free_text_dates(self):
        self.assertEqual(tools().parse_date('31 FEB 1870')['kind'], 'invalid')
        self.assertEqual(tools().parse_date('(about the war)')['kind'], 'text')


class PreImportCheck(unittest.TestCase):
    def test_clean_tree_has_no_issues(self):
        report = tools().check_tree(tools().parse_gedcom(FIXTURES / 'clean.ged'))
        self.assertEqual(report['issues'], [])
        self.assertEqual((report['individuals'], report['families']), (4, 1))

    def test_problem_tree_flags_each_issue(self):
        report = tools().check_tree(tools().parse_gedcom(FIXTURES / 'problems.ged'))
        found = kinds(report)
        for expected in [
            ('death_before_birth', ('@I1@',)),
            ('parent_younger_than_child', ('@I1@', '@I3@')),
            ('parent_younger_than_child', ('@I2@', '@I3@')),
            ('born_after_parent_death', ('@I1@', '@I3@')),
            ('possible_duplicate', ('@I3@', '@I4@')),
            ('implausible_lifespan', ('@I5@',)),
            ('invalid_date', ('@I6@',)),
            ('missing_record', ('@I6@',)),
        ]:
            self.assertIn(expected, found)
        severities = {i['kind']: i['severity'] for i in report['issues']}
        self.assertEqual(severities['possible_duplicate'], 'warning')
        self.assertEqual(severities['death_before_birth'], 'error')

    def test_cli_check_exits_1_on_errors(self):
        run = subprocess.run([sys.executable, str(SCRIPTS / 'gedcom_tools.py'), 'check', str(FIXTURES / 'problems.ged')],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertTrue(json.loads(run.stdout)['issues'])
        clean = subprocess.run([sys.executable, str(ROOT / 'genealogy.py'), 'gedcom', 'check', str(FIXTURES / 'clean.ged')],
                               capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0, clean.stderr)


class Import(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / 'case.json'

    def tearDown(self):
        self.tmp.cleanup()

    def run_import(self, fixture, *extra):
        return subprocess.run([sys.executable, str(SCRIPTS / 'gedcom_tools.py'), 'import', str(FIXTURES / fixture),
                               '--out', str(self.out), *extra], capture_output=True, text=True)

    def test_import_builds_a_valid_provisional_case(self):
        run = self.run_import('clean.ged', '--question', 'Who were Joana Fictícia’s grandparents?')
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        case = json.loads(self.out.read_text(encoding='utf-8'))
        from case_tools import validate_case
        self.assertEqual(validate_case(case, gps=True), [])
        self.assertEqual(case['goal'], 'Who were Joana Fictícia’s grandparents?')
        self.assertEqual(len(case['persons']), 4)
        self.assertTrue(all(p['identity_status'] == 'candidate' for p in case['persons']))
        # The tree is a claim: nothing imported is supported.
        self.assertTrue(case['conclusions'])
        self.assertTrue(all(c['status'] == 'provisional' for c in case['conclusions']))
        self.assertTrue(all(r['status'] == 'provisional' for r in case['relationships']))
        types = sorted(r['type'] for r in case['relationships'])
        self.assertEqual(types, ['parent', 'parent', 'parent', 'parent', 'spouse'])

    def test_the_file_is_the_source_actually_consulted(self):
        self.assertEqual(self.run_import('clean.ged').returncode, 0)
        case = json.loads(self.out.read_text(encoding='utf-8'))
        tree_source = case['sources'][0]
        self.assertEqual(tree_source['source_type'], 'authored')
        self.assertEqual(len(tree_source['sha256']), 64)
        self.assertTrue(all(o['source_id'] == tree_source['id'] for o in case['observations']))
        birth = next(o for o in case['observations'] if o['subject_id'] == 'P-GED-I1' and o['predicate'] == 'birth_date')
        self.assertEqual(birth['value']['literal'], 'ABT 1850')
        self.assertEqual(birth['tree_citations'], [{'title': 'Registo paroquial sintético de Vila Inventada', 'page': 'Livro 1, folha 2'}])
        self.assertIn('@I1@', birth['locator'])
        # The tree's own citations are leads, not sources consulted.
        self.assertEqual(len(case['sources']), 1)

    def test_events_places_and_notes_are_kept(self):
        self.assertEqual(self.run_import('clean.ged').returncode, 0)
        case = json.loads(self.out.read_text(encoding='utf-8'))
        self.assertEqual([p['literal'] for p in case['places']], ['Vila Inventada, Distrito Exemplo'])
        marriage = next(e for e in case['events'] if e['type'] == 'marriage')
        self.assertEqual(sorted(marriage['participant_ids']), ['P-GED-I1', 'P-GED-I2'])
        self.assertTrue(any(o['predicate'] == 'note' and 'emigrated' in o['value'] for o in case['observations']))
        self.assertTrue(any(o['predicate'] == 'baptism_date' for o in case['observations']))

    def test_check_issues_become_tasks_and_import_still_works(self):
        run = self.run_import('problems.ged')
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        case = json.loads(self.out.read_text(encoding='utf-8'))
        self.assertTrue(case['import_check']['issues'])
        self.assertEqual(len(case['tasks']), len(case['import_check']['issues']))
        self.assertTrue(all(t['status'] == 'planned' for t in case['tasks']))
        # Records the tree points at but does not contain are not invented.
        self.assertNotIn('P-GED-F9', json.dumps(case))

    def test_import_refuses_to_overwrite(self):
        self.out.write_text('{}', encoding='utf-8')
        run = self.run_import('clean.ged')
        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.out.read_text(encoding='utf-8'), '{}')


class Docs(unittest.TestCase):
    def test_docs_describe_the_helper(self):
        contracts = (ROOT / 'skills/genealogy-mode/references/tool-contracts.md').read_text(encoding='utf-8')
        self.assertIn('scripts/gedcom_tools.py check', contracts)
        self.assertIn('scripts/gedcom_tools.py import', contracts)
        self.assertNotIn('GEDCOM converter', contracts)
        intake = (ROOT / 'skills/genealogy-case-intake/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('gedcom_tools.py', intake)
        self.assertIn('gedcom', (ROOT / 'README.md').read_text(encoding='utf-8').lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
