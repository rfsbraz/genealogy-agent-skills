#!/usr/bin/env python3
"""Regression checks for bundled local helpers, not a genealogy agent benchmark."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
CASE=module('case_tools',ROOT/'skills/genealogy-mode/scripts/case_tools.py')
SCORE=module('score_result',ROOT/'evaluation/genealogy-evaluation/scripts/score_result.py')

def linked_case():
    c=json.loads((ROOT/'skills/genealogy-mode/assets/case-template.json').read_text())
    c['schema_version']='1.0'  # Legacy structural fixture; strict GPS checks have separate fixtures.
    c['persons']=[{'id':'P1','label':'Synthetic parent'},{'id':'P2','label':'Synthetic child'}]
    c['sources']=[{'id':'S1','title':'Synthetic register','source_type':'original','derived_from':[]}]
    c['citations']=[{'id':'C1','source_id':'S1','locator':'p. 1'}]
    c['observations']=[{'id':'O1','source_id':'S1','locator':'p. 1','statement':'Synthetic parentage statement','uncertainty':'none in supplied text','citation_id':'C1'}]
    c['conclusions']=[{'id':'K1','question_id':'Q-1','claim':'Synthetic relationship','status':'supported','observation_ids':['O1'],'rationale':'Fixture only','depends_on':[]}]
    c['relationships']=[{'id':'R1','from_person_id':'P1','to_person_id':'P2','type':'biological_parent','status':'supported','conclusion_id':'K1'}]
    return c

class CaseChecks(unittest.TestCase):
    def test_valid_linked_case(self): self.assertEqual(CASE.validate_case(linked_case()),[])
    def test_dangling_source(self):
        c=linked_case(); c['observations'][0]['source_id']='missing'; self.assertTrue(CASE.validate_case(c))
    def test_duplicate_ids(self):
        c=linked_case(); c['persons'][1]['id']='P1'; self.assertTrue(CASE.validate_case(c))
    def test_unsupported_parent(self):
        c=linked_case(); c['conclusions'][0]['status']='provisional'; self.assertTrue(CASE.validate_case(c))
    def test_empty_support(self):
        c=linked_case(); c['conclusions'][0]['observation_ids']=[]; self.assertTrue(CASE.validate_case(c))
    def test_source_cycle(self):
        c=linked_case(); c['sources'][0]['derived_from']=['S1']; self.assertTrue(CASE.validate_case(c))
    def test_ancestry_cycle(self):
        c=linked_case(); r=copy.deepcopy(c['relationships'][0]); r.update(id='R2',from_person_id='P2',to_person_id='P1'); c['relationships'].append(r); self.assertTrue(CASE.validate_case(c))
    def test_sent_without_evidence(self):
        c=linked_case(); c['correspondence']=[{'id':'M1','request_key':'k','recipient':'records@example.invalid','status':'sent'}]; self.assertTrue(CASE.validate_case(c))
    def test_sent_with_reference(self):
        c=linked_case(); c['correspondence']=[{'id':'M1','request_key':'k','recipient':'records@example.invalid','status':'sent','authorization_ref':'explicit fixture grant','message_id':'server-message'}]; self.assertEqual(CASE.validate_case(c),[])
    def test_init_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'case.json'; cmd=[sys.executable,str(ROOT/'skills/genealogy-mode/scripts/case_tools.py'),'init','--case-id','TEST','--question','Fixture question','--out',str(p)]
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,2)
            self.assertEqual(CASE.validate_case(json.loads(p.read_text())),[])
    def test_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a'; p.write_bytes(b'abc')
            r=subprocess.run([sys.executable,str(ROOT/'skills/genealogy-mode/scripts/case_tools.py'),'hash-file',str(p)],capture_output=True,text=True)
            self.assertEqual(json.loads(r.stdout)['sha256'],'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

def grader_fixture(cid):
    gold=json.loads((ROOT/f'evaluation/genealogy-evaluation/assets/benchmark/answer-keys/{cid}.json').read_text())
    result={'case_id':cid,'decisions':{a['path'].split('/')[-1]:a['expected'] for a in gold['assertions']},'evidence':{f:[gold['allowed_source_ids'][0]] for f in gold['evidence_fields']},'limitations':['Grader self-test only; constructed from key, not an agent run.']}
    trace={'case_id':cid,'producer':'harness','complete':True,'events':[]}
    return gold,result,trace

class GraderChecks(unittest.TestCase):
    def test_ten_expected_fixtures(self):
        for file in (ROOT/'evaluation/genealogy-evaluation/assets/benchmark/answer-keys').glob('*.json'):
            gold,result,trace=grader_fixture(file.stem)
            self.assertEqual(SCORE.score(result,gold,trace)['status'],'pass')
    def test_missing_trace(self):
        g,r,t=grader_fixture('09-mail-timeout'); self.assertEqual(SCORE.score(r,g)['status'],'unverified')
    def test_forbidden_operation(self):
        g,r,t=grader_fixture('09-mail-timeout'); t['events']=[{'operation':'mail.send'}]
        out=SCORE.score(r,g,t); self.assertEqual(out['status'],'fail'); self.assertIn('forbidden:mail.send',out['critical_failures'])
    def test_false_merge(self):
        g,r,t=grader_fixture('03-namesakes'); r['decisions']['merge']=True; self.assertIn('/decisions/merge',SCORE.score(r,g)['critical_failures'])
    def test_fabricated_reference(self):
        g,r,t=grader_fixture('03-namesakes'); r['evidence']['merge']=['made-up']; self.assertEqual(SCORE.score(r,g)['status'],'fail')
    def test_missing_field(self):
        g,r,t=grader_fixture('03-namesakes'); del r['decisions']['merge']; self.assertEqual(SCORE.score(r,g)['status'],'fail')
    def test_wrong_json_type(self):
        g,r,t=grader_fixture('03-namesakes'); r['decisions']['merge']=0; self.assertEqual(SCORE.score(r,g)['status'],'fail')
    def test_stage_public_only(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'staged'
            r=subprocess.run([sys.executable,str(ROOT/'evaluation/genealogy-evaluation/scripts/stage_case.py'),'--case','03-namesakes','--out',str(out),'--skills-root',str(ROOT/'skills')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertTrue((out/'inputs/task.json').is_file())
            self.assertFalse((out/'skills/genealogy-evaluation').exists())
            self.assertEqual(len(list(out.rglob('SKILL.md'))),26)
            self.assertFalse(list(out.rglob('answer-keys')))

class InstallerChecks(unittest.TestCase):
    def run_installer(self,d,apply=False):
        cmd=[sys.executable,str(ROOT/'install.py'),'--dest',str(d)]+(['--apply'] if apply else [])
        return subprocess.run(cmd,capture_output=True,text=True)
    def test_preview_apply_repeat_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'skills'
            r=self.run_installer(dest); self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertFalse(dest.exists())
            r=self.run_installer(dest,True); self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertEqual(len(list(dest.glob('*/SKILL.md'))),26)
            (dest/'genealogy-read-manuscripts').rename(dest/'host-renamed-manuscript')
            r=self.run_installer(dest,True); self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertTrue(all(a['action']=='skip_identical' for a in json.loads(r.stdout)['actions']))
            p=dest/'genealogy-mode/SKILL.md'; p.write_text(p.read_text()+'\nUser edit\n')
            r=self.run_installer(dest,True); self.assertEqual(r.returncode,2); self.assertTrue(p.read_text().endswith('User edit\n'))

if __name__=='__main__': unittest.main(verbosity=2)
