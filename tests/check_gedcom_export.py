#!/usr/bin/env python3
"""GEDCOM export of reviewed conclusions with their sources, and the loss report. Synthetic fixtures, no network."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills' / 'genealogy-mode' / 'scripts'
FIXTURES = ROOT / 'tests' / 'fixtures' / 'gedcom'
sys.path.insert(0, str(SCRIPTS))

import gedcom_tools  # noqa: E402
from case_tools import validate_case  # noqa: E402

ASSESSMENT = {'basis': 'Compared with the cited synthetic register entry.', 'scope': 'This fact only.',
              'reviewer': 'test reviewer', 'reviewed_on': '2026-10-21', 'known_conflicts': [],
              'limitations': 'Synthetic fixture.'}


def reviewed_case():
    """The clean fixture imported, with three claims promoted to source_supported."""
    case = gedcom_tools.import_tree(gedcom_tools.parse_gedcom(FIXTURES / 'clean.ged'))
    promote = {'CON-GED-I1-BIRT-1', 'CON-GED-F1-I1-I3', 'CON-GED-F1-SPOUSE', 'CON-GED-F1-MARR-1'}
    for row in case['conclusions']:
        if row['id'] in promote:
            row.update(status='source_supported', evidence_assessment=copy.deepcopy(ASSESSMENT))
    for row in case['relationships']:
        if row['conclusion_id'] in promote:
            row['status'] = 'source_supported'
    assert validate_case(case, gps=True) == [], validate_case(case, gps=True)
    return case


class Export(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.case_path = self.dir / 'case.json'
        self.case_path.write_text(json.dumps(reviewed_case(), ensure_ascii=False), encoding='utf-8')
        self.out = self.dir / 'export.ged'

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, *extra, case=None):
        return subprocess.run([sys.executable, str(SCRIPTS / 'gedcom_tools.py'), 'export', str(case or self.case_path),
                               '--out', str(self.out), *extra], capture_output=True, text=True)

    def test_only_reviewed_claims_are_exported(self):
        run = self.export()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        tree = gedcom_tools.parse_gedcom(self.out)
        names = sorted(p['name'] for p in tree['individuals'].values())
        # Abel's parentage and every other claim stayed provisional, so only these three appear.
        self.assertEqual(names, ['Joana Fictícia', 'Rosa Imaginária', 'Tomé Fictício'])
        tome = next(p for p in tree['individuals'].values() if p['name'] == 'Tomé Fictício')
        self.assertEqual([(e['tag'], e['date'], e['place']) for e in tome['events']],
                         [('BIRT', 'ABT 1850', 'Vila Inventada, Distrito Exemplo')])
        joana = next(p for p in tree['individuals'].values() if p['name'] == 'Joana Fictícia')
        self.assertEqual(joana['events'], [])

    def test_families_never_add_an_unreviewed_parent(self):
        self.assertEqual(self.export().returncode, 0)
        tree = gedcom_tools.parse_gedcom(self.out)
        people = {x: p['name'] for x, p in tree['individuals'].items()}
        families = sorted((people.get(f['husband']) or '', people.get(f['wife']) or '', tuple(people[c] for c in f['children']),
                           tuple(e['tag'] for e in f['events'])) for f in tree['families'].values())
        # The couple is reviewed, and so is Tomé as Joana's parent, but Rosa as her parent is not.
        self.assertEqual(families, [('Tomé Fictício', '', ('Joana Fictícia',), ()),
                                    ('Tomé Fictício', 'Rosa Imaginária', (), ('MARR',))])

    def test_every_fact_cites_its_source_with_the_locator(self):
        self.assertEqual(self.export().returncode, 0)
        tree = gedcom_tools.parse_gedcom(self.out)
        self.assertEqual([s['title'] for s in tree['sources'].values()], ['GEDCOM file clean.ged'])
        tome = next(p for p in tree['individuals'].values() if p['name'] == 'Tomé Fictício')
        self.assertEqual(tome['events'][0]['sources'][0]['page'], 'GEDCOM record @I1@')
        for family in tree['families'].values():
            self.assertTrue(family['sources'])
        text = self.out.read_text(encoding='utf-8')
        self.assertIn('Status: source_supported', text)
        self.assertEqual(gedcom_tools.check_tree(tree)['errors'], 0)

    def test_loss_report_lists_what_was_left_out(self):
        self.assertEqual(self.export().returncode, 0)
        report = json.loads(self.out.with_name('export.ged.loss.json').read_text(encoding='utf-8'))
        self.assertEqual(report['exported']['individuals'], 3)
        self.assertEqual(report['exported']['families'], 2)
        self.assertGreater(report['not_exported']['conclusions_by_status']['provisional'], 0)
        self.assertIn('searches', ' '.join(report['always_lost']))
        self.assertEqual(sorted(report['check_before_sharing']), ['P-GED-I1', 'P-GED-I2', 'P-GED-I3'])
        # The tree's sex claims stayed provisional: they only place the couple as HUSB and WIFE.
        self.assertNotIn('1 SEX', self.out.read_text(encoding='utf-8'))
        self.assertEqual(sorted((r['person_id'], r['role']) for r in report['assumed_roles']),
                         [('P-GED-I1', 'HUSB'), ('P-GED-I1', 'HUSB'), ('P-GED-I2', 'WIFE')])

    def test_unexportable_predicates_and_mentions_are_reported(self):
        case = self.dir / 'v14.json'
        case.write_text((ROOT / 'examples/v1.4/case-before.json').read_text(encoding='utf-8'), encoding='utf-8')
        run = self.export(case=case)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        report = json.loads(self.out.with_name('export.ged.loss.json').read_text(encoding='utf-8'))
        self.assertEqual(report['exported']['individuals'], 0)
        self.assertEqual(report['not_exported']['predicates'], {'reported_age': 1})

    def test_provisional_can_be_opted_in_but_not_by_default(self):
        self.assertEqual(self.export('--include', 'provisional', '--report', str(self.dir / 'r.json')).returncode, 0)
        self.assertEqual(len(gedcom_tools.parse_gedcom(self.out)['individuals']), 4)
        self.assertIn('Status: provisional', self.out.read_text(encoding='utf-8'))

    def test_refuses_to_overwrite_and_refuses_invalid_cases(self):
        self.out.write_text('keep', encoding='utf-8')
        self.assertEqual(self.export().returncode, 2)
        self.assertEqual(self.out.read_text(encoding='utf-8'), 'keep')
        self.out.unlink()
        broken = json.loads(self.case_path.read_text(encoding='utf-8'))
        broken['relationships'][0]['conclusion_id'] = 'CON-MISSING'
        bad = self.dir / 'bad.json'
        bad.write_text(json.dumps(broken), encoding='utf-8')
        self.assertEqual(self.export(case=bad).returncode, 2)
        self.assertFalse(self.out.exists())

    def test_long_and_multiline_text_is_wrapped(self):
        lines = gedcom_tools.gedcom_lines(2, 'NOTE', 'a' * 600 + '\nsecond line')
        self.assertTrue(all(len(line) <= 255 for line in lines))
        self.assertEqual(lines[0][:7], '2 NOTE ')
        self.assertTrue(any(line.startswith('3 CONC ') for line in lines))
        self.assertTrue(any(line == '3 CONT second line' for line in lines))


class Docs(unittest.TestCase):
    def test_docs_describe_export(self):
        contracts = (ROOT / 'skills/genealogy-mode/references/tool-contracts.md').read_text(encoding='utf-8')
        self.assertIn('scripts/gedcom_tools.py export', contracts)
        reporting = (ROOT / 'skills/genealogy-reporting/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('gedcom_tools.py export', reporting)
        self.assertIn('gedcom export', (ROOT / 'README.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
