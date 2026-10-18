#!/usr/bin/env python3
"""Packet leakage and agreement-metadata regression checks; no OCR accuracy claim."""
from PIL import Image
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('method_packets', ROOT/'skills/genealogy-read-manuscripts/scripts/method_packets.py')
MODULE = importlib.util.module_from_spec(spec); spec.loader.exec_module(MODULE)


def inputs(folder):
    for name in ('target','line','page','same'):
        Image.new('RGB',(150,30),'white').save(folder/(name+'.png'))
    return {'schema_version':'1.2','source_id':'SYNTHETIC','script':'Latin','round':1,
        'pages':[{'source_id':'SYNTHETIC','page':n,'image':f,'sha256':hashlib.sha256((folder/f).read_bytes()).hexdigest(),'source_locator':'synthetic page '+str(n)} for n,f in [(1,'page.png'),(2,'same.png'),(9,'same.png')]],
        'expected_reading':'SECRET-OLD-TRANSCRIPT',
        'targets':[{'region_id':'R1','page':1,'target_at_line_start':True,'bbox_original':[0,0,150,30],
            'target_image':'target.png','line_image':'line.png','context_image':'page.png',
            'line_bbox_original':[0,0,150,30],'context_bbox_original':[0,0,150,30],
            'same_hand_samples':[{'sample_id':'E1','source_id':'SYNTHETIC','page':2,'bbox_original':[0,0,150,30],'image':'same.png'}]}],
        'verified_context':{'language':'Portuguese','clues':[{'id':'C1','fact':'CONTEXT-ONLY-FACT',
            'provenance':'Synthetic external contextual fixture','independent_of_target':True,'clue_certainty':'certain'}]}}


def manifest():
    return {'source_id':'SYNTHETIC','round':1,'planned_methods':list('ABCD'),
            'packets':{m:{'regions':['R1']} for m in 'ABCD'}}


def reports():
    rows=[]
    for method in 'ABCD':
        product = {MODULE.PRODUCTS[method]: 'Synthetic product, not manuscript evidence'}
        rows.append({'method_id':method,'context_id':'CTX-'+method,'context_isolation':'fresh',
            'model_identity':'same-test-model','round':1,'clue_ids':[], 'status':'completed',
            'execution_kind':sorted(MODULE.EXECUTIONS[method])[-1],
            'spans':[{'region_id':'R1','reading':'literal','alternatives':[],'visible_evidence':[],
                      'conflicts':[],'uncertainty':'fixture','method_product':product}]})
    return rows


class PacketChecks(unittest.TestCase):
    def test_scoped_packets_exclude_old_answers_and_limit_context(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); data=inputs(p); result=MODULE.build(data,p,p/'packets')
            self.assertEqual(set(result['packets']),set('ABCD'))
            self.assertFalse(result['model_diversity_required'])
            for method,row in result['packets'].items():
                prompt=(p/'packets'/row['prompt']).read_text()+(p/'packets'/row['inputs']).read_text()
                self.assertNotIn('SECRET-OLD-TRANSCRIPT',prompt)
                self.assertEqual('CONTEXT-ONLY-FACT' in prompt, method=='D')
                self.assertIn('# Assignment '+method+':',prompt)
                self.assertEqual(len(row['assets']),{'A':1,'B':3,'C':2,'D':3}[method])

    def test_missing_source_fails_without_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); data=inputs(p); (p/'line.png').unlink()
            with self.assertRaises(ValueError): MODULE.build(data,p,p/'packets')
            self.assertFalse((p/'packets').exists())

    def test_circular_or_candidate_context_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory); data=inputs(p)
            data['verified_context']['clues'][0]['independent_of_target']=False
            with self.assertRaises(ValueError): MODULE.build(data,p,p/'packets')
            data=inputs(p);data['verified_context']['expected_reading']='candidate'
            with self.assertRaises(ValueError): MODULE.build(data,p,p/'packets')

    def test_frozen_packets_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);data=inputs(p);MODULE.build(data,p,p/'packets')
            with self.assertRaises(ValueError): MODULE.build(data,p,p/'packets')

    def test_four_same_model_methods_are_valid_but_not_confidence(self):
        out=MODULE.summarize(manifest(),reports())
        self.assertEqual(out['missing_methods'],[])
        self.assertEqual(out['agreement']['R1']['candidate_groups'][0]['methods'],list('ABCD'))
        self.assertEqual(out['agreement']['R1']['confidence'],'not_computed')
        self.assertTrue(any('Shared/unspecified model' in w for w in out['warnings']))

    def test_duplicate_method_does_not_become_fifth_vote(self):
        rows=reports();rows.append(copy.deepcopy(rows[0]))
        with self.assertRaises(ValueError): MODULE.summarize(manifest(),rows)

    def test_generic_repetition_without_method_product_is_rejected(self):
        rows=reports();rows[1]['spans'][0]['method_product']={}
        with self.assertRaises(ValueError): MODULE.summarize(manifest(),rows)

    def test_shared_context_stops_the_panel(self):
        rows=reports();rows[1]['context_id']=rows[0]['context_id']
        with self.assertRaises(MODULE.PanelUnavailable) as caught: MODULE.summarize(manifest(),rows)
        self.assertIn('same context ID',str(caught.exception))

    def test_diacritics_and_spellings_remain_distinct(self):
        rows=reports();rows[0]['spans'][0]['reading']='Jose';rows[1]['spans'][0]['reading']='José'
        out=MODULE.summarize(manifest(),rows)
        self.assertEqual(len(out['agreement']['R1']['candidate_groups']),3)

    def test_missing_and_abstaining_methods_keep_denominator(self):
        rows=reports()[:2];rows[1].update(status='abstained',spans=[])
        out=MODULE.summarize(manifest(),rows)
        self.assertEqual(out['missing_methods'],['C','D'])
        self.assertEqual(out['agreement']['R1']['planned_method_count'],4)
        self.assertEqual(out['agreement']['R1']['methods_without_literal'],['B','C','D'])

    def test_other_round_and_missing_regions_are_rejected(self):
        rows=reports();rows[0]['round']=2
        with self.assertRaises(ValueError): MODULE.summarize(manifest(),rows)
        rows=reports();rows[0]['spans']=[]
        with self.assertRaises(ValueError): MODULE.summarize(manifest(),rows)

    def test_engine_claim_requires_actual_output_metadata(self):
        rows=reports();rows[2]['execution_kind']='htr_engine'
        with self.assertRaises(ValueError): MODULE.summarize(manifest(),rows)
        rows[2]['spans'][0]['method_product']['recognizer']={'tool':'synthetic','model':'fixture','raw_output':'fixture'}
        self.assertEqual(MODULE.summarize(manifest(),rows)['missing_methods'],[])


if __name__ == '__main__': unittest.main(verbosity=2)
