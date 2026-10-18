#!/usr/bin/env python3
"""Synthetic integration checks. They do not measure historical or literary quality."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/genealogy-mode/scripts'))
from case_tools import validate_case
from gps_review import evidence_digest

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
I=module('interview_tools',ROOT/'skills/genealogy-interview/scripts/interview_tools.py')
S=module('story_tools',ROOT/'skills/genealogy-narrative/scripts/story_tools.py')
def turn():return json.loads((ROOT/'skills/genealogy-interview/assets/turn.example.json').read_text())
def seed():return I.apply_turn(I.create_case(),turn(),0)[0]
def story(case):
 return {'schema_version':'1.0','story_id':'ST-ADA','case_id':case['case_id'],'person_id':'P-ADA',
 'evidence_digest':evidence_digest(case),'mode':'evocative','visibility':'private','language':'en','title':'Ada, in recollection',
 'intro_note':'Synthetic demonstration using invented training data.','fiction_notice':'','context_sources':[],
 'blocks':[{'id':'B1','kind':'recollection','basis':'attributed_memory','text':'The participant remembers Ada’s birth as around 1910; her birthplace remains unknown.',
 'observation_ids':['OBS-ADA-BIRTH'],'conclusion_ids':[],'context_ids':[],'note':'Attributed memory, not documentary confirmation.'}],
 'unresolved':['Where was Ada born?']}

class InterviewChecks(unittest.TestCase):
 def test_new_case_is_valid_private_empty(self):
  c=I.create_case();self.assertEqual(validate_case(c,True),[]);self.assertEqual(c['interview']['visibility'],'private');self.assertFalse(c['persons'])
 def test_turn_creates_attributed_provisional_evidence(self):
  c=seed();self.assertEqual(validate_case(c,True),[]);self.assertEqual(c['conclusions'][0]['status'],'provisional');self.assertEqual(c['sources'][0]['source_type'],'testimony');self.assertEqual(c['observations'][0]['value']['kind'],'approximate_year');self.assertEqual(c['interview']['turns'][0]['input']['answer'],turn()['answer'])
 def test_retry_idempotent_even_after_revision_advances(self):
  c=seed();after,changed=I.apply_turn(c,turn(),0);self.assertFalse(changed);self.assertEqual(after,c)
 def test_turn_id_collision_rejected(self):
  t=turn();t['answer']='Different';self.assertRaises(ValueError,I.apply_turn,seed(),t,1)
 def test_stale_revision_rejected(self):
  t=turn();t['id']='TURN-2';self.assertRaises(ValueError,I.apply_turn,seed(),t,0)
 def test_correction_keeps_original(self):
  c=seed();old=c['conclusions'][0]['id'];t=turn();t.update(id='TURN-2',people=[]);a=t['assertions'][0];a.update(id='OBS-2',statement='The participant now thinks around 1912.',value={'literal':'around 1912','kind':'approximate_year','year':1912},supersedes=[old]);t['answer']='Correction: around 1912.'
  updated,_=I.apply_turn(c,t,1);self.assertEqual(updated['conclusions'][0]['status'],'superseded');self.assertEqual(updated['observations'][0],c['observations'][0]);self.assertEqual(len(updated['interview']['turns']),2)
 def test_unknown_skip_pause_resume_no_fake_assertions(self):
  c=seed();t=turn();t.update(id='TURN-2',people=[],assertions=[],answer="I don't know; skip birthplace for now.",action='pause',skip_topics=['birthplace']);t.pop('pending_question');c,_=I.apply_turn(c,t,1);self.assertEqual(c['interview']['status'],'paused');self.assertEqual(len(c['observations']),1);pending=c['interview']['pending_question'];t.update(id='TURN-3',answer='Continue',action='resume');c,_=I.apply_turn(c,t,2);self.assertEqual(c['interview']['pending_question'],pending);self.assertIn('birthplace',c['interview']['skipped_topics'])
 def test_multiple_relationship_types(self):
  t=turn();t['people'] += [{'id':'P-B','label':'B','literal':'B'},{'id':'P-C','label':'C','literal':'C'}]
  base=t['assertions'][0]
  for n,typ,other in [(2,'partner','P-B'),(3,'partner','P-C'),(4,'foster_parent','P-B')]:
   a=copy.deepcopy(base);a.update(id='OBS-'+str(n),predicate=typ,object_person_id=other,value=other);t['assertions'].append(a)
  c,_=I.apply_turn(I.create_case(),t,0);self.assertEqual(len(c['relationships']),3);self.assertTrue(all(r['status']=='provisional' for r in c['relationships']))
 def test_missing_person_and_self_link_fail(self):
  for other in ['P-MISSING','P-ADA']:
   t=turn();t['assertions'][0].update(predicate='partner',object_person_id=other);self.assertRaises(ValueError,I.apply_turn,I.create_case(),t,0)
 def test_unstructured_date_fails(self):
  t=turn();t['assertions'][0]['value']='1910';self.assertRaises(ValueError,I.apply_turn,I.create_case(),t,0)
 def test_reviewed_case_changes_require_maintenance(self):
  c=seed();c['conclusions'][0]['status']='supported';t=turn();t['id']='TURN-2';self.assertRaises(ValueError,I.apply_turn,c,t,1)
 def test_atomic_save_preserves_file_on_bad_turn_and_lock(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'case.json';p.write_text(json.dumps(I.create_case()));before=p.read_bytes();t=turn();t['assertions'][0]['subject_id']='MISSING';self.assertRaises(ValueError,I.save_turn,p,t,0);self.assertEqual(before,p.read_bytes());self.assertFalse(p.with_suffix('.json.lock').exists());p.with_suffix('.json.lock').touch();self.assertRaises(FileExistsError,I.save_turn,p,turn(),0);self.assertEqual(before,p.read_bytes())
 def test_research_handoff_preserves_question_history(self):
  t=turn();t.update(action='research',research_question='Who were Ada’s parents?');c,_=I.apply_turn(I.create_case(),t,0);self.assertEqual(c['interview']['status'],'ready_for_research');self.assertEqual(len(c['questions']),2);self.assertEqual(c['questions'][0]['status'],'queued')
 def test_cli_frontdoor_round_trip(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'case.json';t=Path(d)/'turn.json';t.write_text(json.dumps(turn()))
   for args in [['interview','new','--out',str(p)],['interview','record',str(p),'--turn',str(t),'--expected-revision','0'],['interview','status',str(p)],['check',str(p)]]:
    result=subprocess.run([sys.executable,str(ROOT/'genealogy.py'),*args],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr+result.stdout)

class NarrativeChecks(unittest.TestCase):
 def test_valid_recollection_and_render(self):
  c=seed();s=story(c);self.assertEqual(S.validate_story(c,s),[]);out=S.render_story(c,s);self.assertIn('Behind the story',out);self.assertIn(c['citations'][0]['text'],out);self.assertIn('[^1]',out)
 def test_story_operations_do_not_mutate_case(self):
  c=seed();before=copy.deepcopy(c);S.make_brief(c,'P-ADA');S.render_story(c,story(c));self.assertEqual(c,before)
 def test_unknown_person_and_wrong_case(self):
  c=seed();self.assertRaises(ValueError,S.make_brief,c,'P-NO');s=story(c);s['case_id']='WRONG';self.assertTrue(S.validate_story(c,s))
 def test_stale_evidence_blocks_story(self):
  c=seed();s=story(c);c['observations'][0]['statement']='Changed';self.assertTrue(any('Evidence changed' in e for e in S.validate_story(c,s)))
 def test_testimony_cannot_masquerade_as_documented_record(self):
  c=seed();s=story(c);s['blocks'][0].update(kind='documented',basis='record_statement');self.assertTrue(S.validate_story(c,s))
 def test_provisional_cannot_masquerade_as_reviewed_conclusion(self):
  c=seed();s=story(c);s['blocks'][0].update(kind='documented',basis='reviewed_conclusion',conclusion_ids=[c['conclusions'][0]['id']]);self.assertTrue(S.validate_story(c,s))
 def test_imagined_scene_requires_mode_and_notice(self):
  c=seed();s=story(c);b=s['blocks'][0];b.update(kind='imagined',basis='fiction',observation_ids=[],note='Imagined scene, not recorded.');self.assertTrue(S.validate_story(c,s));s['mode']='novelized';self.assertTrue(S.validate_story(c,s));s['fiction_notice']='A novelized reconstruction with imagined scenes.';self.assertEqual(S.validate_story(c,s),[])
 def test_imagined_scene_cannot_carry_false_evidence(self):
  c=seed();s=story(c);s.update(mode='novelized',fiction_notice='Fiction.');s['blocks'][0].update(kind='imagined',basis='fiction');self.assertTrue(S.validate_story(c,s))
 def test_context_needs_source_and_inference_needs_basis(self):
  c=seed();s=story(c);s['blocks'][0].update(kind='context',basis='historical_context',observation_ids=[]);self.assertTrue(S.validate_story(c,s));s['context_sources']=[{'id':'CTX','citation':'Synthetic context fixture.','locator':'p. 1','consulted_on':'2026-10-17','scope':'Fictional district, 1901.'}];s['blocks'][0]['context_ids']=['CTX'];self.assertEqual(S.validate_story(c,s),[]);s['blocks'][0].update(kind='inference',basis='reasoned_inference',context_ids=[]);self.assertTrue(S.validate_story(c,s))
 def test_duplicate_missing_refs_and_basis_mismatch(self):
  c=seed()
  for change in [{'observation_ids':['MISSING']},{'basis':'fiction'},{'conclusion_ids':['MISSING']}]:
   s=story(c);s['blocks'][0].update(change);self.assertTrue(S.validate_story(c,s))
  s=story(c);s['blocks'].append(copy.deepcopy(s['blocks'][0]));self.assertTrue(S.validate_story(c,s))
 def test_private_output_and_full_citation_required(self):
  c=seed();s=story(c);s['visibility']='public';self.assertTrue(S.validate_story(c,s));s['visibility']='private';c['citations'][0].pop('text');s['evidence_digest']=evidence_digest(c);self.assertTrue(S.validate_story(c,s))
 def test_story_cli_refuses_overwrite(self):
  c=seed()
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);p=d/'case.json';p.write_text(json.dumps(c));b=d/'brief.json';before=p.read_bytes();cmd=[sys.executable,str(ROOT/'genealogy.py'),'story','brief',str(p),'--person','P-ADA','--out',str(b)];self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0);self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0);self.assertEqual(p.read_bytes(),before)

if __name__=='__main__':unittest.main(verbosity=2)
