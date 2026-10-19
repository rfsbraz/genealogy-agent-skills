#!/usr/bin/env python3
"""Synthetic v1.4 regression tests: corrections, scoped findings and projections."""
import copy
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/genealogy-mode/scripts'))
from case_tools import validate_case
from research_updates import apply_reread, current_observations, projection, save_reread, write_projection
from check_gps_countries import reviewed_case
from gps_review import evidence_digest


def fixture():
    case = reviewed_case()
    case['persons'] = [{'id': 'P1', 'label': 'Synthetic Ada'}, {'id': 'P2', 'label': 'Synthetic Manuel'}]
    case['mentions'] = [{'id': 'M1', 'source_id': 'S1', 'locator': 'p. 1, entry 4', 'literal': 'Ada', 'person_id': 'P1'}]
    case['observations'][0].update(subject_id='M1', predicate='reported_age', value=23,
                                  statement='The fixture entry gives age 23.', processing_run_id='RUN-SYNTHETIC-OLD')
    case['conclusions'][0].update(status='source_supported', claim='The fixture entry reports age 23.',
        evidence_assessment={'basis': 'Supplied synthetic statement, no historical claim.',
            'scope': 'Age as reported, not an exact birth date or resolved identity.',
            'reviewer': 'synthetic-test', 'reviewed_on': '2026-10-17', 'known_conflicts': [],
            'limitations': 'Synthetic example; no real source image was read.'})
    case['conclusions'][0].pop('gps_review')
    return case


def replacement():
    obs = copy.deepcopy(fixture()['observations'][0])
    obs.update(id='O2', value=28, statement='The fixture reread gives age 28.', processing_run_id='RUN-SYNTHETIC-NEW')
    return obs


def correct(case, **kwargs):
    args = dict(old_id='O1', reading=replacement(), reason='Synthetic clearer final digit.', actor='synthetic-test', expected_revision=case['revision'])
    args.update(kwargs)
    return apply_reread(case, **args)


class StatusTests(unittest.TestCase):
    def test_scoped_finding_needs_no_full_gps(self):
        self.assertEqual(validate_case(fixture(), gps=True), [])

    def test_assessment_citations_and_conflicts_are_required(self):
        for change in ('assessment', 'citation', 'conflict'):
            c = fixture()
            if change == 'assessment': c['conclusions'][0].pop('evidence_assessment')
            if change == 'citation': c['citations'][0].pop('text')
            if change == 'conflict': c['conclusions'][0]['evidence_assessment']['known_conflicts'] = [{'description':'Different age', 'material':True, 'resolved':False, 'reason':'Unread digit'}]
            self.assertTrue(validate_case(c), change)

    def test_supported_still_requires_full_review(self):
        c = fixture(); c['conclusions'][0]['status'] = 'supported'
        self.assertTrue(validate_case(c))

    def test_old_schema_cannot_mislabel_new_status(self):
        c = fixture(); c['schema_version'] = '1.1'
        self.assertTrue(validate_case(c))


class RereadTests(unittest.TestCase):
    def test_history_current_view_and_dependencies(self):
        c = fixture()
        c['conclusions'].append({'id':'K2','question_id':'Q-1','claim':'Dependent synthetic estimate',
            'status':'provisional','observation_ids':['O1'],'rationale':'Fixture dependency','depends_on':['K1']})
        c['relationships'] = [{'id':'R1','from_person_id':'P1','to_person_id':'P2','type':'household',
                               'status':'provisional','conclusion_id':'K2'}]
        before = copy.deepcopy(c)
        out, changed = correct(c)
        self.assertTrue(changed); self.assertEqual(c, before)
        self.assertEqual(out['observations'][0], before['observations'][0])
        self.assertEqual([o['id'] for o in current_observations(out)], ['O2'])
        self.assertTrue(all(k['review_required'] for k in out['conclusions']))
        self.assertTrue(out['relationships'][0]['review_required'])
        self.assertEqual(out['changes'][-1]['before']['conclusions'][0]['status'], 'source_supported')
        self.assertEqual(validate_case(out, gps=True), [])

    def test_retry_is_noop_but_conflicting_id_is_rejected(self):
        c, _ = correct(fixture())
        out, changed = correct(c, expected_revision=0)
        self.assertFalse(changed); self.assertEqual(out, c)
        with self.assertRaises(ValueError): correct(c, reason='Different reason')

    def test_stale_revision_source_and_run_fail(self):
        with self.assertRaises(ValueError): correct(fixture(), expected_revision=100)
        for key, value in [('source_id','OTHER'), ('processing_run_id','RUN-SYNTHETIC-OLD')]:
            obs = replacement(); obs[key] = value
            with self.assertRaises(ValueError): correct(fixture(), reading=obs)

    def test_chain_allowed_branch_refused(self):
        c, _ = correct(fixture())
        third = replacement(); third.update(id='O3', processing_run_id='RUN-SYNTHETIC-THIRD')
        with self.assertRaises(ValueError): correct(c, reading=third)
        out, _ = correct(c, old_id='O2', reading=third)
        self.assertEqual([o['id'] for o in current_observations(out)], ['O3'])

    def test_review_snapshot_retained_and_digest_refresh_explicit(self):
        c = reviewed_case(); c['observations'][0]['processing_run_id'] = 'RUN-SYNTHETIC-OLD'
        obs = replacement(); obs.pop('subject_id')
        out, _ = correct(c, reading=obs)
        self.assertIn('gps_review', out['changes'][-1]['before']['conclusions'][0])
        self.assertNotIn('gps_review', out['conclusions'][0])
        self.assertEqual(validate_case(out), [])

    def test_cannot_restore_claim_using_superseded_observation(self):
        c, _ = correct(fixture())
        c['conclusions'][0] = fixture()['conclusions'][0]
        self.assertTrue(any('superseded' in e for e in validate_case(c)))

    def test_global_review_refresh_propagates_to_unrelated_dependents(self):
        c = reviewed_case()
        other = copy.deepcopy(c['observations'][0]); other.update(id='O-OTHER', processing_run_id='RUN-OLD-OTHER')
        c['observations'].append(other)
        dependent = fixture()['conclusions'][0]
        dependent.update(id='K2', depends_on=['K1'])
        c['conclusions'].append(dependent)
        c['conclusions'][0]['gps_review']['evidence_digest'] = evidence_digest(c)
        self.assertEqual(validate_case(c), [])
        new = copy.deepcopy(other); new.update(id='O-NEW', processing_run_id='RUN-NEW-OTHER')
        out, _ = correct(c, old_id='O-OTHER', reading=new)
        self.assertEqual(validate_case(out), [])
        self.assertEqual(out['changes'][-1]['gps_refresh_ids'], ['K1','K2'])

    def test_superseded_review_is_archived_without_reviving_claim(self):
        c=reviewed_case(); c['conclusions'][0]['status']='superseded'
        c['conclusions'][0]['gps_review']['evidence_digest']=evidence_digest(c)
        self.assertEqual(validate_case(c),[])
        obs=replacement(); obs.pop('subject_id')
        out,_=correct(c,reading=obs)
        self.assertEqual(validate_case(out),[])
        self.assertEqual(out['conclusions'][0]['status'],'superseded')
        self.assertIn('gps_review',out['changes'][-1]['before']['conclusions'][0])

    def test_failed_disk_replace_preserves_input_and_cleans_lock(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'case.json'; p.write_text(json.dumps(fixture()))
            before = p.read_bytes()
            with patch('research_updates.os.replace', side_effect=OSError('fixture failure')):
                with self.assertRaises(OSError): save_reread(p, old_id='O1', reading=replacement(), reason='Correct digit', actor='test', expected_revision=0)
            self.assertEqual(p.read_bytes(), before)
            self.assertEqual([x.name for x in Path(d).iterdir()], ['case.json'])


class ExternalRunTests(unittest.TestCase):
    def external(self, **run):
        obs = replacement(); obs.pop('processing_run_id')
        obs['external_run'] = {'ref': 'host-ledger:entry-0042', **run}
        return obs

    def test_external_run_is_accepted_and_marked(self):
        out, changed = correct(fixture(), reading=self.external(system='host text ledger'))
        self.assertTrue(changed)
        new = out['observations'][-1]
        self.assertNotIn('processing_run_id', new)
        self.assertEqual(new['external_run'], {'kind': 'external', 'ref': 'host-ledger:entry-0042', 'system': 'host text ledger'})
        self.assertEqual(out['changes'][-1]['external_run'], new['external_run'])
        self.assertEqual(validate_case(out, gps=True), [])
        fact = projection(out)['data/facts/S1.json']['facts'][0]
        self.assertIsNone(fact['processing_run_id']); self.assertEqual(fact['external_run']['kind'], 'external')

    def test_queue_run_change_and_fact_stay_unchanged(self):
        out, _ = correct(fixture())
        self.assertNotIn('external_run', out['changes'][-1])
        self.assertNotIn('external_run', projection(out)['data/facts/S1.json']['facts'][0])

    def test_reread_without_any_run_reference_fails(self):
        obs = replacement(); obs.pop('processing_run_id')
        with self.assertRaises(ValueError): correct(fixture(), reading=obs)

    def test_bad_external_references_fail(self):
        both = self.external(); both['processing_run_id'] = 'RUN-SYNTHETIC-NEW'
        empty = self.external(); empty['external_run']['ref'] = '  '
        wrong_kind = self.external(kind='queue')
        not_object = replacement(); not_object.pop('processing_run_id'); not_object['external_run'] = 'host-ledger:entry-0042'
        for name, obs in [('both', both), ('empty', empty), ('kind', wrong_kind), ('shape', not_object)]:
            with self.subTest(name):
                with self.assertRaises(ValueError): correct(fixture(), reading=obs)

    def test_external_reread_needs_a_new_external_run(self):
        c, _ = correct(fixture(), reading=self.external())
        again = self.external(); again['id'] = 'O3'
        with self.assertRaises(ValueError): correct(c, old_id='O2', reading=again)
        again['external_run']['ref'] = 'host-ledger:entry-0043'
        out, _ = correct(c, old_id='O2', reading=again)
        self.assertEqual([o['id'] for o in current_observations(out)], ['O3'])

    def test_cli_external_run_flag(self):
        with tempfile.TemporaryDirectory() as d:
            case = Path(d)/'case.json'; case.write_text(json.dumps(fixture()))
            reading = Path(d)/'reading.json'; obs = replacement(); obs.pop('processing_run_id'); reading.write_text(json.dumps(obs))
            base = [sys.executable, str(ROOT/'genealogy.py'), 'reread', str(case), '--old', 'O1', '--reading', str(reading),
                    '--reason', 'Synthetic clearer final digit.', '--actor', 'synthetic-test', '--expected-revision', '0']
            r = subprocess.run(base, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            r = subprocess.run(base + ['--external-run', 'host-ledger:entry-0042'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            saved = json.loads(case.read_text())['observations'][-1]
            self.assertEqual(saved['external_run'], {'kind': 'external', 'ref': 'host-ledger:entry-0042'})


SINGLE = {'method_id': 'single', 'context_isolation': 'fresh', 'context_id': 'ctx-synthetic-1',
          'model_identity': 'host-default-unspecified', 'execution_kind': 'visual_reading', 'status': 'completed'}


class ReadingMethodTests(unittest.TestCase):
    def block(self, **method):
        return {'methods': [{**SINGLE, **method}]}

    def test_reading_method_is_kept_and_projected(self):
        obs = replacement(); obs['reading_method'] = self.block()
        out, _ = correct(fixture(), reading=obs)
        self.assertEqual(validate_case(out, gps=True), [])
        self.assertEqual(out['observations'][-1]['reading_method'], self.block())
        self.assertEqual(projection(out)['data/facts/S1.json']['facts'][0]['reading_method'], self.block())

    def test_unknown_values_are_rejected(self):
        bad = [self.block(context_isolation='isolated'), self.block(method_id='E'), self.block(status='done'),
               self.block(context_id=' '), {'methods': []}, {}]
        for block in bad:
            with self.subTest(block=block):
                c = fixture(); c['observations'][0]['reading_method'] = block
                self.assertTrue(validate_case(c, gps=True))

    def test_not_blind_double_reading_is_valid(self):
        block = {'methods': [{**SINGLE, 'method_id': m, 'context_isolation': 'shared', 'context_id': 'ctx-synthetic-shared'}
                             for m in ('not_blind', 'context')]}
        c = fixture(); c['observations'][0]['reading_method'] = block
        self.assertEqual(validate_case(c, gps=True), [])

    def test_every_documented_text_form_parses_to_a_valid_block(self):
        text = (ROOT / 'skills/genealogy-read-manuscripts/references/protocol.md').read_text(encoding='utf-8')
        lines = re.findall(r'^reading_method: .+$', text, re.M)
        self.assertTrue(any('method_id=not_blind' in line for line in lines), 'no not_blind example in protocol.md')
        for line in lines:
            block = {'methods': [dict(field.strip().split('=', 1) for field in method.split(','))
                                 for method in line.split(':', 1)[1].split(';')]}
            with self.subTest(line=line[:60]):
                c = fixture(); c['observations'][0]['reading_method'] = block
                self.assertEqual(validate_case(c, gps=True), [])

    def test_documented_text_form_parses_to_a_valid_block(self):
        text = (ROOT / 'skills/genealogy-read-manuscripts/references/protocol.md').read_text(encoding='utf-8')
        line = re.search(r'^reading_method: .+$', text, re.M).group(0)
        block = {'methods': [dict(field.strip().split('=', 1) for field in method.split(','))
                             for method in line.split(':', 1)[1].split(';')]}
        c = fixture(); c['observations'][0]['reading_method'] = block
        self.assertEqual(validate_case(c, gps=True), [])


class ProjectionTests(unittest.TestCase):
    def test_current_facts_and_flagged_notes_from_same_input(self):
        c, _ = correct(fixture()); before = copy.deepcopy(c)
        p = projection(c)
        self.assertEqual(c, before)
        self.assertEqual(p['data/facts/S1.json']['facts'][0]['value'], 28)
        note = p['data/tree-notes.json']['people']['P1'][0]
        self.assertTrue(note['review_required']); self.assertEqual(note['status'], 'provisional')
        self.assertEqual(p, projection(c))

    def test_tree_preserves_manual_fields_and_regenerates_own_notes(self):
        c = fixture(); tree = {'people':[{'id':'Ada','notes':['Handwritten note']},{'id':'Manuel'}], 'custom':42}
        mapping = {'documents':{'S1':'DOC-001'},'persons':{'P1':'Ada','P2':'Manuel'},
                   'tree_person_pointers':{'P1':'/people/0','P2':'/people/1'}}
        before = copy.deepcopy(tree)
        p = projection(c, mapping, tree); out = p['data/tree.json']
        self.assertEqual(tree, before); self.assertEqual(out['custom'],42)
        self.assertEqual(out['people'][0]['notes'], ['Handwritten note'])
        self.assertEqual(out, projection(c, mapping, out)['data/tree.json'])
        self.assertIn('data/facts/DOC-001.json',p)
        self.assertEqual(out['people'][0]['research_notes'][0]['evidence_assessment'], c['conclusions'][0]['evidence_assessment'])

    def test_unsafe_filename_identity_merge_and_invalid_pointer_fail(self):
        c=fixture()
        for mapping in ({'documents':{'S1':'../escape'}}, {'persons':{'P1':'same','P2':'same'}},
                        {'persons':{'P1':None}}, {'persons':{'P1':'  '}}):
            with self.assertRaises(ValueError): projection(c,mapping)
        with self.assertRaises(ValueError): projection(c, {}, {'people':[]})

    def test_pointer_alias_cannot_merge_people(self):
        c=fixture()
        mapping={'tree_person_pointers':{'P1':'/people/0','P2':'/people/00'}}
        with self.assertRaises(ValueError): projection(c,mapping,{'people':[{}]})

    def test_old_generated_notes_removed_after_person_remapping(self):
        c=fixture(); old={'generated_by':'genealogy-case','case_id':c['case_id'],'text':'Stale'}
        other={'generated_by':'genealogy-case','case_id':'OTHER-CASE','text':'Keep'}
        tree={'people':[{'research_notes':[old,other,'Manual']},{},{}]}
        mapping={'tree_person_pointers':{'P1':'/people/1','P2':'/people/2'}}
        result=projection(c,mapping,tree)['data/tree.json']
        self.assertEqual(result['people'][0]['research_notes'],[other,'Manual'])

    def test_no_overwrite_and_no_input_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'build'; write_projection(fixture(),out)
            original = (out/'data/facts/S1.json').read_bytes()
            with self.assertRaises(ValueError): write_projection(fixture(),out)
            self.assertEqual((out/'data/facts/S1.json').read_bytes(), original)

    def test_cli_routes_both_commands(self):
        for command in ('reread','project'):
            r = subprocess.run([sys.executable,str(ROOT/'genealogy.py'),command,'--help'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr); self.assertIn(command,r.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
