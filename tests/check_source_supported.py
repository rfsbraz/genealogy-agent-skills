#!/usr/bin/env python3
"""Scoped source-supported findings: schema, validator edge cases and the status card."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'skills/genealogy-mode/assets'
sys.path.insert(0, str(ROOT / 'skills/genealogy-mode/scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from case_tools import validate_case
from check_v14 import fixture


class SchemaVersion(unittest.TestCase):
    def test_template_emits_1_2_and_schema_reads_all_versions(self):
        self.assertEqual(json.loads((ASSETS / 'case-template.json').read_text())['schema_version'], '1.2')
        schema = json.loads((ASSETS / 'case.schema.json').read_text())
        self.assertEqual(schema['properties']['schema_version']['enum'], ['1.0', '1.1', '1.2'])

    def test_status_enum_and_assessment_shape(self):
        text = (ASSETS / 'case.schema.json').read_text()
        self.assertEqual(text.count('"source_supported"'), 2)
        self.assertIn('"evidence_assessment"', text)


class Validator(unittest.TestCase):
    def test_assessment_date_must_be_iso(self):
        case = fixture()
        case['conclusions'][0]['evidence_assessment']['reviewed_on'] = '17/10/2026'
        self.assertTrue(any('YYYY-MM-DD' in e for e in validate_case(case)))

    def test_resolved_or_immaterial_conflicts_are_allowed(self):
        case = fixture()
        case['conclusions'][0]['evidence_assessment']['known_conflicts'] = [
            {'description': 'Index gives another age', 'material': True, 'resolved': True, 'reason': 'Index misread the digit'}]
        self.assertEqual(validate_case(case), [])

    def test_relationship_needs_an_assessed_conclusion(self):
        case = fixture()
        case['relationships'] = [{'id': 'R1', 'from_person_id': 'P1', 'to_person_id': 'P2', 'type': 'household',
                                  'status': 'source_supported', 'conclusion_id': 'K1'}]
        self.assertEqual(validate_case(case), [])
        weaker = copy.deepcopy(case)
        weaker['conclusions'][0]['status'] = 'provisional'
        self.assertTrue(any('assessed conclusion' in e for e in validate_case(weaker)))


class StatusCard(unittest.TestCase):
    def test_status_labels_source_supported_plainly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'case.json'
            path.write_text(json.dumps(fixture()), encoding='utf-8')
            out = subprocess.run([sys.executable, str(ROOT / 'genealogy.py'), 'status', str(path)],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn('Source-supported; full proof review pending: The fixture entry reports age 23.', out.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)


class PublishedWorkingTreeDocs(unittest.TestCase):
    def test_gps_policy_covers_shared_working_and_published_tree(self):
        gps = (ROOT / 'skills/genealogy-mode/references/gps-policy.md').read_text(encoding='utf-8')
        adapter = (ROOT / 'skills/genealogy-mode/references/host-adapter.md').read_text(encoding='utf-8')
        contract = (ROOT / 'skills/genealogy-mode/references/shared-contract.md').read_text(encoding='utf-8')
        self.assertIn('When the working tree is also the published tree', gps)
        self.assertIn('must not create an ancestry edge', gps)
        self.assertIn('publish build filters conclusions by status', adapter)
        self.assertIn('not an accepted proof-reviewed ancestry edge', contract)
