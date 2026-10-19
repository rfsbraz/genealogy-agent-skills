#!/usr/bin/env python3
"""Synthetic local-ledger tests; no model, OCR or private documents are used."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys
import hashlib
import sqlite3
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
METHOD={'methods':[{'method_id':'single','context_isolation':'fresh','context_id':'ctx-synthetic-1',
                    'model_identity':'host-default-unspecified','execution_kind':'visual_reading','status':'completed'}]}
SCRIPT=ROOT/'skills/genealogy-document-processing/scripts/document_queue.py'
spec=importlib.util.spec_from_file_location('queue',SCRIPT); q=importlib.util.module_from_spec(spec); spec.loader.exec_module(q)

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.base=Path(self.temp.name); self.path=self.base/'ledger.sqlite'; self.db=q.connect(self.path,True)
        self.art=self.base/'synthetic-reading.md'; self.art.write_text('Synthetic text. No historical claim or actual reading.\n')
        self.record={'document_id':'DOC1','source_id':'SRC1','page_count':250,'sha256':'a'*64,'location':{'kind':'fixture','path':'example.invalid'}}
        self.version=q.register(self.db,self.record)['version_id']
    def tearDown(self): self.db.close(); self.temp.cleanup()
    def allowance(self,n=10000):
        now=datetime.now(timezone.utc)
        return q.budget(self.db,'W1',n,(now-timedelta(hours=1)).isoformat(),(now+timedelta(hours=1)).isoformat())
    def results(self,pages,coverage='full',review=False,tokens=100):
        return {'metadata':{'method':'synthetic_fixture','skill_version':'test','reading_method':json.loads(json.dumps(METHOD))},'actual_tokens':tokens,
                'artifacts':[{'id':'A','path':str(self.art)}],
                'pages':[{'page':p,'coverage':coverage,'requires_review':review,'artifact_id':'A','locator':'#p'+str(p),'note':'Synthetic fixture'} for p in pages]}
    def run_job(self,mode='quick',pages=[1],coverage='full',review=False,tokens=100,reread=None):
        q.plan(self.db,'DOC1',mode,pages,2,100,50,3,reread)
        job=q.claim(self.db,'worker',mode)['job']
        return q.finish(self.db,job['id'],'worker',self.results(job['pages'],coverage,review,tokens))
    def test_registration_idempotent(self):
        self.assertFalse(q.register(self.db,self.record)['created'])
        with self.assertRaises(ValueError): q.register(self.db,{**self.record,'page_count':249})
    def test_computed_hash(self):
        record={**self.record,'document_id':'LOCAL','sha256':q.hash_file(self.art)}
        vid=q.register(self.db,record,self.art)['version_id']
        self.assertEqual(self.db.execute('SELECT hash_method FROM versions WHERE id=?',(vid,)).fetchone()[0],'computed')
    def test_250_page_backlog_and_dedup(self):
        a=q.plan(self.db,'DOC1','detailed',batch_pages=2,tokens_per_page=100)
        self.assertEqual(len(a['created_jobs']),125)
        self.assertEqual(q.plan(self.db,'DOC1','detailed',tokens_per_page=100)['created_jobs'],[])
    def test_no_active_budget(self):
        q.plan(self.db,'DOC1','quick',[1],tokens_per_page=100)
        self.assertEqual(q.claim(self.db,'worker')['status'],'no_active_allowance')
    def test_budget_skip_large_job(self):
        self.allowance(150)
        q.plan(self.db,'DOC1','detailed',[1,2],tokens_per_page=100,priority=90)
        q.plan(self.db,'DOC1','detailed',[3],tokens_per_page=100,priority=30)
        self.assertEqual(q.claim(self.db,'worker')['job']['pages'],[3])
    def test_budget_cannot_reset_or_overlap(self):
        self.allowance()
        with self.assertRaises(ValueError): self.allowance(20000)
        now=datetime.now(timezone.utc)
        with self.assertRaises(ValueError): q.budget(self.db,'W2',100,now.isoformat(),(now+timedelta(hours=2)).isoformat())
    def test_claim_retry_preserves_running_job(self):
        self.allowance(); q.plan(self.db,'DOC1','quick',[1,2],1,100)
        one=q.claim(self.db,'worker'); two=q.claim(self.db,'worker')
        self.assertEqual(two['status'],'worker_already_running'); self.assertEqual(two['job_id'],one['job']['id'])
    def test_concurrent_claims_and_reservations(self):
        self.allowance(200); q.plan(self.db,'DOC1','quick',[1,2,3],1,100)
        def work(worker):
            db=q.connect(self.path)
            try: return q.claim(db,worker)
            finally: db.close()
        with ThreadPoolExecutor(max_workers=2) as pool: out=list(pool.map(work,['w1','w2']))
        self.assertEqual(len({r['job']['id'] for r in out}),2)
        self.assertEqual(q.claim(self.db,'w3')['status'],'no_fitting_job')
    def test_extraction_does_not_promote_reading(self):
        self.allowance(); self.run_job('extract',[1,2])
        s=q.status(self.db,'DOC1')['full_coverage']; self.assertEqual(s['extract']['count'],2); self.assertEqual(s['quick']['count'],0); self.assertEqual(s['detailed']['count'],0)
    def test_partial_does_not_complete_page(self):
        self.allowance(); self.run_job('detailed',[1],coverage='partial')
        s=q.status(self.db,'DOC1'); self.assertEqual(s['full_coverage']['detailed']['count'],0); self.assertEqual(s['pages_with_partial_attempts'],[1])
        self.assertEqual(len(q.plan(self.db,'DOC1','detailed',[1],tokens_per_page=100)['created_jobs']),1)
    def test_missing_page_rejected_without_settlement(self):
        self.allowance(); q.plan(self.db,'DOC1','quick',[1,2],tokens_per_page=100); job=q.claim(self.db,'w')['job']
        with self.assertRaises(ValueError): q.finish(self.db,job['id'],'w',self.results([1]))
        self.assertEqual(self.db.execute('SELECT state FROM jobs WHERE id=?',(job['id'],)).fetchone()[0],'running')
        self.assertEqual(self.db.execute('SELECT spent FROM windows').fetchone()[0],0)
    def test_missing_artifact_rejected(self):
        self.allowance(); q.plan(self.db,'DOC1','quick',[1],tokens_per_page=100); job=q.claim(self.db,'w')['job']
        r=self.results([1]); r['artifacts'][0]['path']=str(self.base/'missing')
        with self.assertRaises(ValueError): q.finish(self.db,job['id'],'w',r)
    def test_usage_unknown_and_overrun(self):
        self.allowance(200); out=self.run_job(tokens=None); self.assertEqual((out['charged_tokens'],out['usage_kind']),(100,'estimated'))
        self.run_job(pages=[2],tokens=250)
        q.plan(self.db,'DOC1','quick',[3],tokens_per_page=100)
        self.assertEqual(q.claim(self.db,'next')['available_tokens'],-150)
    def test_detailed_finish_needs_reading_method(self):
        self.allowance(); q.plan(self.db,'DOC1','detailed',[1],tokens_per_page=100); job=q.claim(self.db,'w')['job']
        missing=self.results([1]); missing['metadata'].pop('reading_method')
        bad=self.results([1]); bad['metadata']['reading_method']['methods'][0]['context_isolation']='isolated'
        for result in (missing,bad):
            with self.assertRaisesRegex(ValueError,'reading_method'): q.finish(self.db,job['id'],'w',result)
        self.assertEqual(self.db.execute('SELECT state FROM jobs WHERE id=?',(job['id'],)).fetchone()[0],'running')
        q.finish(self.db,job['id'],'w',self.results([1]))
        self.assertEqual(json.loads(self.db.execute('SELECT metadata FROM runs').fetchone()[0])['reading_method'],METHOD)
    def test_quick_finish_checks_reading_method_only_when_given(self):
        self.allowance(); q.plan(self.db,'DOC1','quick',[1],tokens_per_page=100); job=q.claim(self.db,'w')['job']
        bad=self.results([1]); bad['metadata']['reading_method']['methods'][0]['context_isolation']='isolated'
        with self.assertRaisesRegex(ValueError,'reading_method'): q.finish(self.db,job['id'],'w',bad)
        missing=self.results([1]); missing['metadata'].pop('reading_method')
        self.assertEqual(q.finish(self.db,job['id'],'w',missing)['job_state'],'completed')
    def test_reading_method_values_match_case_schema(self):
        schema=json.loads((ROOT/'skills/genealogy-mode/assets/case.schema.json').read_text(encoding='utf-8'))
        item=schema['$defs']['reading_method']['properties']['methods']['items']
        self.assertEqual({k:tuple(item['properties'][k]['enum']) for k in q.READING_METHOD},q.READING_METHOD)
        self.assertEqual(set(item['required']),set(q.READING_METHOD)|set(q.METHOD_TEXT_FIELDS))
    def test_double_finish_does_not_double_charge(self):
        self.allowance(); out=self.run_job(); job=self.db.execute('SELECT job_id FROM runs WHERE id=?',(out['run_id'],)).fetchone()[0]
        with self.assertRaises(ValueError): q.finish(self.db,job,'worker',self.results([1]))
        self.assertEqual(self.db.execute('SELECT spent FROM windows').fetchone()[0],100)
    def test_source_change_resets_current_coverage(self):
        self.allowance(); self.run_job(); q.plan(self.db,'DOC1','detailed',[2],tokens_per_page=100)
        new=q.register(self.db,{**self.record,'sha256':'b'*64})
        self.assertNotEqual(new['version_id'],self.version)
        self.assertEqual(q.status(self.db,'DOC1')['full_coverage']['quick']['count'],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM jobs WHERE state='cancelled'").fetchone()[0],1)
    def test_rereading_retains_history_and_review(self):
        self.allowance(); self.run_job('quick',[1],review=True)
        self.run_job('detailed',[1],coverage='partial',review=False)
        self.assertEqual(q.status(self.db,'DOC1')['review_required_pages'],[1])
        self.run_job('detailed',[1],review=False)
        self.assertEqual(q.status(self.db,'DOC1')['review_required_pages'],[])
        self.run_job('detailed',[1],review=True,reread='scheduled blind audit')
        self.assertEqual(q.status(self.db,'DOC1')['review_required_pages'],[1])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],4)
    def test_attempt_limit(self):
        self.allowance()
        for _ in range(3): self.run_job('quick',[1],coverage='failed')
        self.assertEqual(q.plan(self.db,'DOC1','quick',[1],tokens_per_page=100)['skipped']['attempt_limit'],[1])
        self.assertEqual(len(q.plan(self.db,'DOC1','quick',[1],tokens_per_page=100,reread_reason='access restored')['created_jobs']),1)
    def test_historical_import_no_new_model_usage(self):
        result=self.results([1,2]); result['metadata'].update(external_run_id='legacy-1',original_read_on='2026-10-11')
        out=q.import_history(self.db,'DOC1','quick',result); self.assertEqual(out['charged_tokens'],0)
        self.assertFalse(q.import_history(self.db,'DOC1','quick',result)['created'])
        self.assertEqual(q.status(self.db,'DOC1')['full_coverage']['quick']['count'],2)
    def test_documented_import_example_is_accepted(self):
        cli=(ROOT/'skills/genealogy-document-processing/references/cli.md').read_text(encoding='utf-8')
        section=cli.split('## Import prior readings',1)[1].split('\n## ',1)[0]
        for field in ('metadata.method','metadata.skill_version','metadata.external_run_id','metadata.original_read_on'):
            self.assertIn(field, section)
        self.assertIn('Use `unknown` when the reading predates these skills', section)
        block=re.search(r'```json\n(\{.*?\n\})\n```', section, re.S).group(1)
        result=json.loads(block)
        art=self.base/Path(result['artifacts'][0]['path'])
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text('Imported historical reading fixture.\n')
        result['artifacts'][0]['path']=str(art)
        q.register(self.db,{'document_id':'DOC-EXAMPLE','source_id':'DOC-EXAMPLE','page_count':1,'sha256':'c'*64,
                            'location':{'kind':'fixture','path':'example.invalid'}})
        out=q.import_history(self.db,'DOC-EXAMPLE','quick',result)
        self.assertTrue(out['created']); self.assertEqual(out['charged_tokens'],0)
        missing={**result,'metadata':{k:v for k,v in result['metadata'].items() if k!='skill_version'}}
        missing['metadata']['external_run_id']='legacy-example-missing-version'
        with self.assertRaises(ValueError) as ctx: q.import_history(self.db,'DOC-EXAMPLE','quick',missing)
        self.assertIn('skill_version', str(ctx.exception))
    def test_cancel_running_rejected(self):
        self.allowance(); q.plan(self.db,'DOC1','quick',[1],tokens_per_page=100); job=q.claim(self.db,'worker')['job']
        with self.assertRaises(ValueError): q.cancel(self.db,job['id'],'cancel')
    def test_out_of_range_and_invalid_bool(self):
        with self.assertRaises(ValueError): q.plan(self.db,'DOC1','quick',[251],tokens_per_page=100)
        with self.assertRaises(ValueError): q.plan(self.db,'DOC1','quick',[True],tokens_per_page=100)
    def test_export_and_cli(self):
        export=q.export_data(self.db); self.assertEqual(len(export['tables']['versions']),1)
        r=subprocess.run([sys.executable,str(SCRIPT),'--db',str(self.path),'status','--doc','DOC1'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertEqual(json.loads(r.stdout)['page_count'],250)

    def image_set(self,hashes=('1'*64,'2'*64,'3'*64)):
        return {'document_id':'SET1','source_id':'SRC-SET1','location':{'kind':'fixture','path':'example.invalid/register'},
                'images':[{'page':n,'filename':'img-%03d.jpg'%n,'sha256':h} for n,h in enumerate(hashes,1)]}
    def test_image_set_registers_one_version_with_every_page_hash(self):
        out=q.register(self.db,self.image_set()); self.assertTrue(out['created'])
        v=self.db.execute('SELECT * FROM versions WHERE id=?',(out['version_id'],)).fetchone()
        self.assertEqual(v['page_count'],3); self.assertEqual(v['hash_method'],'manifest_reported')
        expected=hashlib.sha256(''.join('%d %s\n'%(n,h) for n,h in [(1,'1'*64),(2,'2'*64),(3,'3'*64)]).encode()).hexdigest()
        self.assertEqual(v['sha256'],expected)
        rows=[tuple(r) for r in self.db.execute('SELECT page,locator,sha256 FROM version_pages WHERE version_id=? ORDER BY page',(out['version_id'],))]
        self.assertEqual(rows,[(1,'img-001.jpg','1'*64),(2,'img-002.jpg','2'*64),(3,'img-003.jpg','3'*64)])
    def test_image_set_reregister_is_noop_and_changed_image_is_new_version(self):
        first=q.register(self.db,self.image_set())
        again=q.register(self.db,self.image_set()); self.assertEqual((again['created'],again['version_id']),(False,first['version_id']))
        changed=q.register(self.db,self.image_set(('1'*64,'f'*64,'3'*64)))
        self.assertTrue(changed['created']); self.assertNotEqual(changed['version_id'],first['version_id'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM version_pages').fetchone()[0],6)
        self.assertEqual(q.current(self.db,'SET1')['id'],changed['version_id'])
    def test_claim_returns_image_hash_for_each_assigned_page(self):
        q.register(self.db,self.image_set()); self.allowance()
        q.plan(self.db,'SET1','quick',[2,3],2,100)
        job=q.claim(self.db,'worker','quick')['job']
        self.assertEqual(job['source']['images'],[{'page':2,'locator':'img-002.jpg','sha256':'2'*64},{'page':3,'locator':'img-003.jpg','sha256':'3'*64}])
    def test_single_file_claim_has_no_image_list(self):
        self.allowance(); q.plan(self.db,'DOC1','quick',[1],1,100)
        self.assertNotIn('images',q.claim(self.db,'worker')['job']['source'])
    def test_image_set_rejects_dishonest_or_broken_manifests(self):
        good=self.image_set()
        cases={'gap':{**good,'images':[{**good['images'][0]},{**good['images'][2]}]},
               'reordered':{**good,'images':list(reversed(good['images']))},
               'count':{**good,'page_count':4},
               'both_hashes':{**good,'sha256':'a'*64},
               'no_locator':{**good,'images':[{'page':1,'sha256':'1'*64}]},
               'bad_hash':{**good,'images':[{'page':1,'filename':'x.jpg','sha256':'xyz'}]},
               'empty':{**good,'images':[]}}
        for name,record in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError): q.register(self.db,record)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM documents WHERE id='SET1'").fetchone()[0],0)
    def test_image_set_cli_computes_hashes_from_folder(self):
        folder=self.base/'images'; folder.mkdir()
        for n in (1,2): (folder/('img-%03d.jpg'%n)).write_bytes(b'synthetic image %d'%n)
        record={'document_id':'SET2','source_id':'SRC-SET2','location':{'kind':'local','path':'images'},
                'images':[{'page':n,'filename':'img-%03d.jpg'%n} for n in (1,2)]}
        rec=self.base/'set.json'; rec.write_text(json.dumps(record))
        r=subprocess.run([sys.executable,str(SCRIPT),'--db',str(self.path),'register','--record',str(rec),'--images-dir',str(folder)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        v=q.current(self.db,'SET2'); self.assertEqual((v['hash_method'],v['page_count']),('manifest_computed',2))
        self.assertEqual(self.db.execute('SELECT sha256 FROM version_pages WHERE version_id=? AND page=2',(v['id'],)).fetchone()[0],q.hash_file(folder/'img-002.jpg'))
        record['document_id']='SET3'; record['images'][0]['sha256']='0'*64
        with self.assertRaises(ValueError): q.register(self.db,record,images_dir=folder)
    def test_schema_1_database_is_upgraded_in_place(self):
        old=self.base/'old.sqlite'; con=sqlite3.connect(old); con.executescript(q.SCHEMA)
        con.execute("INSERT INTO documents(id,source_id) VALUES ('OLD','SRC-OLD')"); con.commit(); con.close()
        db=q.connect(old)
        try:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
            self.assertEqual(db.execute("SELECT source_id FROM documents WHERE id='OLD'").fetchone()[0],'SRC-OLD')
            self.assertEqual(q.export_data(db)['tables']['version_pages'],[])
        finally: db.close()
    def test_export_includes_page_images(self):
        q.register(self.db,self.image_set()); export=q.export_data(self.db)
        self.assertEqual(export['schema_version'],2); self.assertEqual(len(export['tables']['version_pages']),3)
    def populated(self):
        self.allowance(); self.run_job('quick',[1,2]); self.run_job('detailed',[3],coverage='partial',review=True)
        q.plan(self.db,'DOC1','detailed',[4,5],tokens_per_page=100)
        stale=q.plan(self.db,'DOC1','extract',[6],tokens_per_page=100)['created_jobs'][0]['job_id']; q.cancel(self.db,stale,'synthetic cancel')
        old=self.results([7]); old['metadata'].update(external_run_id='legacy-7',original_read_on='unknown'); q.import_history(self.db,'DOC1','quick',old)
        return q.export_data(self.db)
    def test_restore_round_trip_is_identical(self):
        export=self.populated(); target=q.connect(self.base/'restored.sqlite',True)
        try:
            out=q.restore(target,json.loads(json.dumps(export)))
            self.assertEqual(out['rows']['runs'],3)
            self.assertEqual(q.export_data(target)['tables'],export['tables'])
            self.assertEqual(q.status(target,'DOC1'),q.status(self.db,'DOC1'))
            self.assertEqual(q.plan(target,'DOC1','quick',[1,2],tokens_per_page=100)['skipped']['already_full'],[1,2])
        finally: target.close()
    def test_restore_refuses_nonempty_database(self):
        export=self.populated()
        with self.assertRaises(ValueError): q.restore(self.db,export)
    def test_restore_rejects_bad_export_and_leaves_database_empty(self):
        export=self.populated(); target=q.connect(self.base/'restored.sqlite',True)
        self.assertEqual(export['schema_version'],2)
        old_version={**export,'schema_version':1}; future_version={**export,'schema_version':3}
        missing={**export,'tables':{k:v for k,v in export['tables'].items() if k!='runs'}}
        extra_column=json.loads(json.dumps(export)); extra_column['tables']['jobs'][0]['surprise']=1
        orphan=json.loads(json.dumps(export)); orphan['tables']['versions']=[]
        try:
            for bad in (old_version,future_version,missing,extra_column,orphan,[],{'schema_version':1}):
                with self.subTest(bad=str(bad)[:40]):
                    with self.assertRaises((ValueError,q.sqlite3.Error)): q.restore(target,bad)
                    self.assertEqual(sum(len(v) for v in q.export_data(target)['tables'].values()),0)
        finally: target.close()
    def test_restore_cli_creates_cache_from_export(self):
        self.populated(); exported=self.base/'export.json'; cache=self.base/'cache'/'queue.sqlite'
        run=lambda *a:subprocess.run([sys.executable,str(SCRIPT),*a],capture_output=True,text=True)
        r=run('--db',str(self.path),'export','--out',str(exported)); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        r=run('--db',str(cache),'restore','--from',str(exported)); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(json.loads(r.stdout)['status'],'restored')
        r=run('--db',str(cache),'restore','--from',str(exported)); self.assertEqual(r.returncode,2,r.stdout+r.stderr)
        self.assertEqual(q.export_data(q.connect(cache))['tables'],json.loads(exported.read_text())['tables'])

if __name__=='__main__': unittest.main(verbosity=2)
