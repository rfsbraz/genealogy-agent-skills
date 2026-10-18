#!/usr/bin/env python3
"""The host adapter contract for repositories that stay canonical.

Deterministic: synthetic example data only, no network, no model calls.
"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COORDINATOR = ROOT / 'skills/genealogy-mode'
SCRIPT = COORDINATOR / 'scripts/host_adapter.py'
CONTRACT = COORDINATOR / 'assets/host-adapter-contract.json'
DOC = COORDINATOR / 'references/host-adapter.md'
EXAMPLE = ROOT / 'examples/host-adapter'
CASE = ROOT / 'examples/v1.4/case-before.json'
CLASSES = {'required', 'optional', 'sidecar_only'}


def load_helper():
    spec = importlib.util.spec_from_file_location('host_adapter', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


class Contract(unittest.TestCase):
    def test_every_case_section_has_one_class(self):
        contract = read(CONTRACT)
        schema = read(COORDINATOR / 'assets/case.schema.json')
        self.assertEqual(set(contract['sections']), set(schema['required']))
        for name, rule in contract['sections'].items():
            with self.subTest(section=name):
                self.assertIn(rule['class'], CLASSES)

    def test_issue_minimum_classes(self):
        sections = read(CONTRACT)['sections']
        for name in ('observations', 'conclusions', 'persons', 'sources', 'citations'):
            self.assertEqual(sections[name]['class'], 'required', name)
        for name in ('hypotheses', 'searches', 'tasks'):
            self.assertEqual(sections[name]['class'], 'optional', name)
        fields = read(CONTRACT)['fields']
        self.assertEqual(fields['conclusions.evidence_assessment']['class'], 'optional')
        self.assertEqual(read(CONTRACT)['sidecar']['path'], 'research/cases/<case-id>.json')

    def test_doc_lists_every_section_with_its_class(self):
        doc = DOC.read_text(encoding='utf-8')
        contract = read(CONTRACT)
        for name, rule in list(contract['sections'].items()) + list(contract['fields'].items()):
            with self.subTest(section=name):
                self.assertIn('| `' + name + '` | ' + rule['class'] + ' |', doc)
        for heading in ('## Export', '## Import', '## Round trip check', '## What stays out'):
            self.assertIn(heading, doc)

    def test_skill_and_revisions_link_to_the_contract(self):
        skill = (COORDINATOR / 'SKILL.md').read_text(encoding='utf-8')
        revisions = (COORDINATOR / 'references/revisions-and-projections.md').read_text(encoding='utf-8')
        self.assertIn('(references/host-adapter.md)', skill)
        self.assertIn('(host-adapter.md)', revisions)


class SplitAndMerge(unittest.TestCase):
    def setUp(self):
        self.helper = load_helper()
        self.contract = self.helper.load_contract()
        self.case = read(CASE)

    def test_split_then_merge_gives_the_same_case(self):
        for host_stores in (set(), {'searches', 'conclusions.evidence_assessment'}):
            with self.subTest(host_stores=sorted(host_stores)):
                host, sidecar = self.helper.split(self.case, self.contract, host_stores)
                self.assertEqual(self.helper.sidecar_errors(sidecar, self.contract), [])
                self.assertEqual(self.helper.merge(host, sidecar, self.contract), self.case)

    def test_reading_method_lives_in_the_host_or_the_sidecar(self):
        case = copy.deepcopy(self.case)
        case['observations'][0]['reading_method'] = {'methods': [{'method_id': 'single', 'context_isolation': 'fresh',
            'context_id': 'ctx-synthetic-1', 'model_identity': 'host-default-unspecified',
            'execution_kind': 'visual_reading', 'status': 'completed'}]}
        host, sidecar = self.helper.split(case, self.contract, set())
        self.assertNotIn('reading_method', host['observations'][0])
        self.assertEqual(self.helper.sidecar_errors(sidecar, self.contract), [])
        self.assertEqual(self.helper.merge(host, sidecar, self.contract), case)
        host, _ = self.helper.split(case, self.contract, {'observations.reading_method'})
        self.assertEqual(host['observations'][0]['reading_method'], case['observations'][0]['reading_method'])

    def test_sidecar_never_holds_host_facts(self):
        _, sidecar = self.helper.split(self.case, self.contract, set())
        self.assertNotIn('observations', sidecar['sections'])
        self.assertIn('searches', sidecar['sections'])
        bad = copy.deepcopy(sidecar)
        bad['sections']['observations'] = self.case['observations']
        errors = self.helper.sidecar_errors(bad, self.contract)
        self.assertTrue(any('observations' in e for e in errors), errors)
        bad = copy.deepcopy(sidecar)
        bad['fields']['conclusions'] = {'K1': {'claim': 'edited outside the host'}}
        errors = self.helper.sidecar_errors(bad, self.contract)
        self.assertTrue(any('conclusions.claim' in e for e in errors), errors)


class ExampleAdapter(unittest.TestCase):
    def run_check(self, folder, adapter='adapter.py'):
        command = [sys.executable, str(SCRIPT), 'check',
                   '--export', sys.executable + ' ' + adapter + ' export',
                   '--import', sys.executable + ' ' + adapter + ' import',
                   '--sidecar', 'research/cases/C-EXAMPLE.json']
        return subprocess.run(command, cwd=folder, capture_output=True, text=True)

    def copy_example(self, tmp):
        folder = Path(tmp) / 'host'
        shutil.copytree(EXAMPLE, folder)
        return folder

    def test_example_round_trip_is_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.copy_example(tmp)
            run = self.run_check(folder)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)['round_trip'], 'identical')

    def test_example_exports_the_shipped_synthetic_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.copy_example(tmp)
            out = subprocess.run([sys.executable, 'adapter.py', 'export'], cwd=folder, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(out.stdout), read(CASE))

    def test_example_accepts_a_reread_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.copy_example(tmp)
            case = Path(tmp) / 'case.json'
            out = subprocess.run([sys.executable, 'adapter.py', 'export'], cwd=folder, capture_output=True, text=True, check=True)
            case.write_text(out.stdout, encoding='utf-8')
            subprocess.run([sys.executable, str(ROOT / 'genealogy.py'), 'reread', str(case), '--old', 'O1',
                            '--reading', str(ROOT / 'examples/v1.4/replacement.json'), '--reason', 'Synthetic clearer final digit.',
                            '--actor', 'synthetic-test', '--expected-revision', '0'], check=True, capture_output=True)
            subprocess.run([sys.executable, 'adapter.py', 'import', str(case)], cwd=folder, check=True, capture_output=True)
            again = subprocess.run([sys.executable, 'adapter.py', 'export'], cwd=folder, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(again.stdout), read(case))
            sidecar = read(folder / 'research/cases/C-EXAMPLE.json')
            self.assertNotIn('observations', sidecar['sections'])
            self.assertEqual(self.run_check(folder).returncode, 0)

    def test_adapter_that_drops_a_section_fails_the_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.copy_example(tmp)
            source = (folder / 'adapter.py').read_text(encoding='utf-8')
            marker = 'def import_case(case):\n'
            self.assertIn(marker, source)
            (folder / 'lossy.py').write_text(source.replace(marker, marker + "    case = dict(case, searches=[])\n"), encoding='utf-8')
            run = self.run_check(folder, 'lossy.py')
            self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
            self.assertIn('searches', run.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
