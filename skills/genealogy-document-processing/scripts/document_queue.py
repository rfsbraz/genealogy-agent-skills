#!/usr/bin/env python3
"""Local document coverage and budget queue. No network, model calls or timer."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import uuid

MODES=('extract','quick','detailed')
EXPORT_SCHEMA_VERSION=2
TABLES=('documents','versions','version_pages','windows','jobs','runs','page_results')
SCHEMA='''
CREATE TABLE documents(id TEXT PRIMARY KEY, source_id TEXT NOT NULL, current_version TEXT);
CREATE TABLE versions(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
 sha256 TEXT NOT NULL, page_count INTEGER NOT NULL CHECK(page_count>0), location TEXT NOT NULL,
 hash_method TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(document_id,sha256));
CREATE TABLE windows(id TEXT PRIMARY KEY, starts_at TEXT NOT NULL, ends_at TEXT NOT NULL,
 token_limit INTEGER NOT NULL CHECK(token_limit>=0), spent INTEGER NOT NULL DEFAULT 0);
CREATE TABLE jobs(id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES versions(id),
 mode TEXT NOT NULL CHECK(mode IN ('extract','quick','detailed')), pages TEXT NOT NULL,
 priority INTEGER NOT NULL, estimated_tokens INTEGER NOT NULL CHECK(estimated_tokens>0),
 state TEXT NOT NULL CHECK(state IN ('queued','running','completed','partial','failed','cancelled')),
 reason TEXT NOT NULL, created_at TEXT NOT NULL, claimed_at TEXT, worker TEXT,
 window_id TEXT REFERENCES windows(id), reserved_tokens INTEGER NOT NULL DEFAULT 0);
CREATE TABLE runs(id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
 version_id TEXT NOT NULL REFERENCES versions(id), mode TEXT NOT NULL,
 metadata TEXT NOT NULL, artifacts TEXT NOT NULL, finished_at TEXT NOT NULL,
 charged_tokens INTEGER NOT NULL, usage_kind TEXT NOT NULL);
CREATE TABLE page_results(run_id TEXT NOT NULL REFERENCES runs(id), page INTEGER NOT NULL,
 coverage TEXT NOT NULL CHECK(coverage IN ('full','partial','failed')), requires_review INTEGER NOT NULL,
 details TEXT NOT NULL, PRIMARY KEY(run_id,page));
CREATE INDEX jobs_ready ON jobs(state,priority,created_at);
PRAGMA user_version=1;
'''
# Schema 2 adds one image per page for versions registered from an image set.
MIGRATION_2='''
CREATE TABLE version_pages(version_id TEXT NOT NULL REFERENCES versions(id), page INTEGER NOT NULL CHECK(page>0),
 locator TEXT NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(version_id,page));
PRAGMA user_version=2;
'''

def now(): return datetime.now(timezone.utc).isoformat(timespec='microseconds')
def uid(prefix): return prefix+'-'+uuid.uuid4().hex
def dumps(obj): return json.dumps(obj,ensure_ascii=False,sort_keys=True)
def require(value,message):
    if not value: raise ValueError(message)
def integer(value,name,minimum=0):
    require(type(value) is int and value>=minimum,name+' must be an integer >= '+str(minimum)); return value
def text_field(value,name):
    require(isinstance(value,str) and bool(value.strip()),name+' must be nonempty text'); return value
def timestamp(value):
    date=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(date.tzinfo is not None,'Timestamp needs a timezone')
    return date.astimezone(timezone.utc).isoformat(timespec='microseconds')
READING_METHOD={'method_id':('A','B','C','D','single','blind','context'),'context_isolation':('fresh','shared','unknown'),
                'status':('completed','partial','abstained','blocked')}
METHOD_TEXT_FIELDS=('context_id','model_identity','execution_kind')
def reading_method(block):
    require(isinstance(block,dict) and isinstance(block.get('methods'),list) and block['methods'],
            'metadata.reading_method must be an object with a nonempty methods list; detailed runs require it (see genealogy-read-manuscripts references/protocol.md)')
    for method in block['methods']:
        require(isinstance(method,dict),'Each metadata.reading_method method must be an object')
        for field,allowed in READING_METHOD.items(): require(method.get(field) in allowed,'metadata.reading_method '+field+' must be one of: '+', '.join(allowed))
        for field in METHOD_TEXT_FIELDS: text_field(method.get(field),'metadata.reading_method '+field)
def hash_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): digest.update(b)
    return digest.hexdigest()

def connect(path,initialize=False):
    path=Path(path)
    require(initialize or path.is_file(),'Database does not exist; run init')
    if initialize: path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=30,isolation_level=None)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    version=db.execute('PRAGMA user_version').fetchone()[0]
    if version==0 and initialize:
        require(not db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),'Refusing to initialize an unrelated database')
        db.executescript('BEGIN IMMEDIATE;'+SCHEMA+MIGRATION_2+'COMMIT;')
    elif version==1: db.executescript('BEGIN IMMEDIATE;'+MIGRATION_2+'COMMIT;')
    else: require(version==2,'Unsupported or uninitialized database schema')
    return db

@contextmanager
def transaction(db,write=True):
    db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
    try: yield; db.execute('COMMIT')
    except BaseException: db.execute('ROLLBACK'); raise

def valid_hash(value,message):
    require(isinstance(value,str) and re.fullmatch('[0-9a-fA-F]{64}',value),message); return value.lower()

def image_pages(images,images_dir=None):
    """Check an ordered image list and return its page rows and the version hash.

    The version hash is the SHA-256 of one line per image, in page order:
    "<page> <lowercase sha256>\\n". Locators are not part of it."""
    require(isinstance(images,list) and images,'images must be a nonempty list')
    pages=[]
    for n,image in enumerate(images,1):
        require(isinstance(image,dict),'Each image must be an object')
        require(image.get('page')==n and type(image.get('page')) is int,'Image pages must be 1, 2, 3 ... in list order')
        locator=image.get('filename',image.get('locator'))
        text_field(locator,'image filename or locator')
        if images_dir is not None:
            name=text_field(image.get('filename'),'image filename (needed with --images-dir)')
            digest=hash_file(Path(images_dir)/name)
            if image.get('sha256'): require(digest==valid_hash(image['sha256'],'Valid image SHA-256 required'),'Local image hash differs from record for page '+str(n))
        else: digest=valid_hash(image.get('sha256'),'Valid image SHA-256 required for page '+str(n))
        pages.append((n,locator,digest))
    total=hashlib.sha256(''.join('%d %s\n'%(n,h) for n,_,h in pages).encode()).hexdigest()
    return pages,total

def register(db,record,local_file=None,images_dir=None):
    require(isinstance(record,dict),'Registration record must be an object')
    doc=text_field(record.get('document_id'),'document_id')
    source=text_field(record.get('source_id'),'source_id')
    location=record.get('location'); require(isinstance(location,dict) and location,'location must be a nonempty object')
    pages=None
    if 'images' in record:
        require(local_file is None and 'sha256' not in record,'Give either images or one source file/sha256, not both')
        pages,digest=image_pages(record['images'],images_dir); method='manifest_computed' if images_dir is not None else 'manifest_reported'
        count=len(pages)
        if 'page_count' in record: require(record['page_count']==count,'page_count must equal the number of images')
    else:
        require(images_dir is None,'--images-dir needs an images list in the record')
        count=integer(record.get('page_count'),'page_count',1)
        digest=valid_hash(hash_file(local_file) if local_file else record.get('sha256'),'Valid source SHA-256 required')
        if local_file and record.get('sha256'): require(digest==record['sha256'].lower(),'Local source hash differs from record')
        method='computed' if local_file else 'reported'
    with transaction(db):
        old=db.execute('SELECT * FROM documents WHERE id=?',(doc,)).fetchone()
        require(not old or old['source_id']==source,'Document source_id cannot silently change')
        same=db.execute('SELECT * FROM versions WHERE document_id=? AND sha256=?',(doc,digest)).fetchone()
        if same:
            require(same['page_count']==count,'Same source hash has a different page count')
            return {'version_id':same['id'],'created':False,'current':old['current_version']==same['id']}
        if not old: db.execute('INSERT INTO documents(id,source_id) VALUES (?,?)',(doc,source))
        version=uid('V')
        db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?,?)',(version,doc,digest,count,dumps(location),method,now()))
        for page in pages or []: db.execute('INSERT INTO version_pages VALUES (?,?,?,?)',(version,*page))
        db.execute('UPDATE documents SET current_version=? WHERE id=?',(version,doc))
        if old:
            db.execute("UPDATE jobs SET state='cancelled',reason=reason || '; source superseded' WHERE version_id=? AND state='queued'",(old['current_version'],))
        return {'version_id':version,'created':True,'current':True}

def current(db,doc):
    row=db.execute('SELECT v.* FROM documents d JOIN versions v ON v.id=d.current_version WHERE d.id=?',(doc,)).fetchone()
    require(row is not None,'Unknown document'); return row

def selected_pages(spec,count):
    if spec is None: return list(range(1,count+1))
    if isinstance(spec,list): pages=spec
    else:
        pages=[]
        for part in spec.split(','):
            match=re.fullmatch(r'(\d+)(?:-(\d+))?',part.strip()); require(match,'Invalid page specification')
            a=int(match[1]); b=int(match[2] or a); require(a<=b,'Reversed page range'); pages.extend(range(a,b+1))
    require(pages and all(type(n) is int and 1<=n<=count for n in pages),'Pages out of range')
    return sorted(set(pages))

def plan(db,doc,mode,pages=None,batch_pages=2,tokens_per_page=1000,priority=50,max_attempts=3,reread_reason=None):
    require(mode in MODES,'Unknown mode'); integer(batch_pages,'batch_pages',1); integer(tokens_per_page,'tokens_per_page',1)
    integer(priority,'priority'); require(priority<=100,'priority must be <=100'); integer(max_attempts,'max_attempts',1)
    if reread_reason is not None: text_field(reread_reason,'reread_reason')
    with transaction(db):
        ver=current(db,doc); wanted=selected_pages(pages,ver['page_count']); pending=set(); attempts={}
        for row in db.execute('SELECT pages,state FROM jobs WHERE version_id=? AND mode=?',(ver['id'],mode)):
            for page in json.loads(row['pages']):
                if row['state'] in ('queued','running'): pending.add(page)
                elif row['state'] in ('completed','partial','failed'): attempts[page]=attempts.get(page,0)+1
        full={r[0] for r in db.execute("SELECT p.page FROM page_results p JOIN runs r ON r.id=p.run_id WHERE r.version_id=? AND r.mode=? AND p.coverage='full'",(ver['id'],mode))}
        skipped={'already_full':[],'pending':[],'attempt_limit':[]}; ready=[]
        for page in wanted:
            if page in pending: skipped['pending'].append(page)
            elif page in full and not reread_reason: skipped['already_full'].append(page)
            elif attempts.get(page,0)>=max_attempts and not reread_reason: skipped['attempt_limit'].append(page)
            else: ready.append(page)
        jobs=[]
        for offset in range(0,len(ready),batch_pages):
            chunk=ready[offset:offset+batch_pages]; job=uid('J')
            db.execute('INSERT INTO jobs(id,version_id,mode,pages,priority,estimated_tokens,state,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                       (job,ver['id'],mode,dumps(chunk),priority,len(chunk)*tokens_per_page,'queued',reread_reason or 'missing full coverage',now()))
            jobs.append({'job_id':job,'pages':chunk,'estimated_tokens':len(chunk)*tokens_per_page})
        return {'version_id':ver['id'],'created_jobs':jobs,'skipped':skipped}

def budget(db,window_id,tokens,starts_at,ends_at):
    text_field(window_id,'window_id'); integer(tokens,'tokens'); start=timestamp(starts_at); end=timestamp(ends_at); require(start<end,'Window must have positive duration')
    with transaction(db):
        old=db.execute('SELECT * FROM windows WHERE id=?',(window_id,)).fetchone()
        if old:
            require((old['starts_at'],old['ends_at'],old['token_limit'])==(start,end,tokens),'Cannot reset an existing allowance ID')
            return {'window_id':window_id,'created':False}
        require(not db.execute('SELECT id FROM windows WHERE starts_at<? AND ends_at>?',(end,start)).fetchone(),'Budget windows must not overlap')
        db.execute('INSERT INTO windows(id,starts_at,ends_at,token_limit) VALUES (?,?,?,?)',(window_id,start,end,tokens))
        return {'window_id':window_id,'created':True}

def claim(db,worker,mode=None):
    text_field(worker,'worker')
    if mode is not None: require(mode in MODES,'Unknown mode')
    with transaction(db):
        running=db.execute("SELECT id FROM jobs WHERE state='running' AND worker=?",(worker,)).fetchone()
        if running: return {'status':'worker_already_running','job_id':running['id']}
        time=now(); window=db.execute('SELECT * FROM windows WHERE starts_at<=? AND ends_at>?',(time,time)).fetchone()
        if not window: return {'status':'no_active_allowance'}
        reserved=db.execute("SELECT COALESCE(SUM(reserved_tokens),0) FROM jobs WHERE window_id=? AND state='running'",(window['id'],)).fetchone()[0]
        available=window['token_limit']-window['spent']-reserved
        sql="SELECT j.* FROM jobs j JOIN documents d ON j.version_id=d.current_version WHERE j.state='queued' AND j.estimated_tokens<=?"
        args=[available]
        if mode: sql+=' AND j.mode=?'; args.append(mode)
        sql+=' ORDER BY j.priority DESC,j.created_at,j.id LIMIT 1'
        job=db.execute(sql,args).fetchone()
        if not job: return {'status':'no_fitting_job','available_tokens':available}
        db.execute("UPDATE jobs SET state='running',worker=?,claimed_at=?,window_id=?,reserved_tokens=estimated_tokens WHERE id=?",(worker,time,window['id'],job['id']))
        row=dict(db.execute('SELECT * FROM jobs WHERE id=?',(job['id'],)).fetchone()); row['pages']=json.loads(row['pages'])
        row['source']=dict(db.execute('SELECT * FROM versions WHERE id=?',(job['version_id'],)).fetchone()); row['source']['location']=json.loads(row['source']['location'])
        images=[dict(r) for r in db.execute('SELECT page,locator,sha256 FROM version_pages WHERE version_id=? ORDER BY page',(job['version_id'],)) if r['page'] in row['pages']]
        if images: row['source']['images']=images
        return {'status':'claimed','job':row,'available_tokens_after_reservation':available-job['estimated_tokens']}

def finish(db,job_id,worker,result):
    require(isinstance(result,dict),'Result must be an object')
    metadata=result.get('metadata'); require(isinstance(metadata,dict),'metadata object required')
    text_field(metadata.get('method'),'metadata.method'); text_field(metadata.get('skill_version'),'metadata.skill_version')
    usage=result.get('actual_tokens')
    if usage is not None: integer(usage,'actual_tokens')
    artifacts=[]; seen=set()
    for artifact in result.get('artifacts',[]):
        require(isinstance(artifact,dict),'Artifact must be an object'); aid=text_field(artifact.get('id'),'artifact.id'); require(aid not in seen,'Duplicate artifact ID'); seen.add(aid)
        path=Path(text_field(artifact.get('path'),'artifact.path')).resolve(); require(path.is_file(),'Artifact file missing')
        digest=hash_file(path)
        if artifact.get('sha256'): require(artifact['sha256']==digest,'Artifact hash mismatch')
        artifacts.append({'id':aid,'path':str(path),'sha256':digest})
    pages=result.get('pages'); require(isinstance(pages,list) and pages,'Page results required')
    numbers=[]
    for p in pages:
        require(isinstance(p,dict),'Page result must be an object'); integer(p.get('page'),'page',1); numbers.append(p['page'])
        require(p.get('coverage') in ('full','partial','failed'),'Invalid coverage')
        require(type(p.get('requires_review')) is bool,'requires_review must be boolean')
        if p['coverage']!='failed':
            require(p.get('artifact_id') in seen,'Processed page needs a registered artifact'); text_field(p.get('locator'),'page artifact locator')
        else: text_field(p.get('note'),'Failure reason')
    require(len(numbers)==len(set(numbers)),'Duplicate page result')
    with transaction(db):
        job=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone(); require(job is not None,'Unknown job')
        require(job['state']=='running' and job['worker']==worker,'Job is not running under this worker')
        if job['mode']=='detailed' or 'reading_method' in metadata: reading_method(metadata.get('reading_method'))
        require(sorted(numbers)==json.loads(job['pages']),'Results must account for every assigned page, including failures')
        charged=job['reserved_tokens'] if usage is None else usage; run=uid('RUN')
        db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)',(run,job_id,job['version_id'],job['mode'],dumps(metadata),dumps(artifacts),now(),charged,'estimated' if usage is None else 'measured'))
        for p in pages: db.execute('INSERT INTO page_results VALUES (?,?,?,?,?)',(run,p['page'],p['coverage'],int(p['requires_review']),dumps(p)))
        state='completed' if all(p['coverage']=='full' for p in pages) else ('failed' if all(p['coverage']=='failed' for p in pages) else 'partial')
        db.execute('UPDATE jobs SET state=?,reserved_tokens=0 WHERE id=?',(state,job_id))
        db.execute('UPDATE windows SET spent=spent+? WHERE id=?',(charged,job['window_id']))
        return {'run_id':run,'job_state':state,'charged_tokens':charged,'usage_kind':'estimated' if usage is None else 'measured'}

def cancel(db,job_id,reason):
    text_field(reason,'reason')
    with transaction(db):
        job=db.execute('SELECT state FROM jobs WHERE id=?',(job_id,)).fetchone(); require(job is not None and job['state']=='queued','Only queued jobs can be cancelled; reconcile running work first')
        db.execute("UPDATE jobs SET state='cancelled',reason=reason || ? WHERE id=?",('; cancelled: '+reason,job_id))
    return {'job_id':job_id,'state':'cancelled'}

def import_history(db,doc,mode,result):
    require(mode in MODES,'Unknown mode'); require(isinstance(result,dict),'Result must be an object')
    result=json.loads(dumps(result)); metadata=result.get('metadata')
    require(isinstance(metadata,dict),'metadata object required')
    key=text_field(metadata.get('external_run_id'),'metadata.external_run_id')
    text_field(metadata.get('original_read_on'),'metadata.original_read_on; use unknown when unavailable')
    metadata['origin']='historical_import'; metadata['original_actual_tokens']=result.get('actual_tokens')
    result['actual_tokens']=0
    with transaction(db):
        ver=current(db,doc)
        for old in db.execute('SELECT id,metadata FROM runs WHERE version_id=? AND mode=?',(ver['id'],mode)):
            if json.loads(old['metadata']).get('external_run_id')==key:
                return {'run_id':old['id'],'created':False,'note':'Existing imported run; use a new external_run_id for corrected metadata or artifacts.'}
        pages=result.get('pages'); require(isinstance(pages,list) and pages,'Page results required')
        assigned=selected_pages([p.get('page') for p in pages],ver['page_count'])
        job='IMPORT-'+hashlib.sha256(dumps([ver['id'],mode,key]).encode()).hexdigest()
        require(not db.execute('SELECT id FROM jobs WHERE id=?',(job,)).fetchone(),'This historical import is already in progress; reconcile it first')
        worker=uid('IMPORTER')
        db.execute('INSERT INTO jobs(id,version_id,mode,pages,priority,estimated_tokens,state,reason,created_at,claimed_at,worker) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                   (job,ver['id'],mode,dumps(assigned),0,1,'running','historical import; no reading executed',now(),now(),worker))
    try:
        out=finish(db,job,worker,result); out.update(created=True,note='Historical import; zero new model usage. Original usage remains in metadata.'); return out
    except BaseException:
        with transaction(db): db.execute("DELETE FROM jobs WHERE id=? AND state='running'",(job,))
        raise

def status(db,doc):
    with transaction(db,False):
        ver=current(db,doc); full={m:set() for m in MODES}; touched=set(); partial=set(); review=set()
        rows=db.execute('SELECT p.*,r.mode FROM page_results p JOIN runs r ON r.id=p.run_id WHERE r.version_id=? ORDER BY r.finished_at,r.id',(ver['id'],)).fetchall()
        for row in rows:
            page=row['page']; touched.add(page)
            if row['coverage']=='full': full[row['mode']].add(page)
            if row['coverage']=='partial': partial.add(page)
            if row['requires_review']: review.add(page)
            elif row['mode']=='detailed' and row['coverage']=='full': review.discard(page)
        jobs={r['state']:r['n'] for r in db.execute('SELECT state,COUNT(*) AS n FROM jobs WHERE version_id=? GROUP BY state',(ver['id'],))}
        return {'document_id':doc,'version_id':ver['id'],'page_count':ver['page_count'],
                'full_coverage':{m:{'count':len(s),'pages':sorted(s)} for m,s in full.items()},
                'never_attempted_pages':sorted(set(range(1,ver['page_count']+1))-touched),
                'pages_with_partial_attempts':sorted(partial),'review_required_pages':sorted(review),'jobs':jobs,
                'note':'Coverage sets overlap. Full scope does not establish accurate text or historical truth.'}

def export_data(db):
    with transaction(db,False):
        return {'schema_version':EXPORT_SCHEMA_VERSION,'exported_at':now(),'tables':{t:[dict(r) for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in TABLES}}

def read_json(value,flag='JSON file'):
    """Load a JSON file argument; '-' reads stdin. Errors name the argument and never echo inline JSON."""
    if value=='-': text,name=sys.stdin.read(),'stdin'
    else:
        require(not value.lstrip().startswith(('{','[')),flag+': expected a file path, got inline JSON. Save the JSON to a file and pass its path, or pass - to read it from stdin.')
        path=Path(value); require(path.is_file(),flag+': file not found: '+value)
        text,name=path.read_text(encoding='utf-8'),value
    try: return json.loads(text)
    except json.JSONDecodeError as e: raise ValueError(flag+': '+name+' is not valid JSON ('+e.msg+', line '+str(e.lineno)+')') from None

JSON_FILE='path to a JSON {} file, or - to read it from stdin'

def restore(db,data):
    """Rebuild an empty queue database from an export, row for row, in one transaction."""
    require(isinstance(data,dict) and data.get('schema_version')==EXPORT_SCHEMA_VERSION,'Export must be an object with schema_version %d' % EXPORT_SCHEMA_VERSION)
    tables=data.get('tables'); require(isinstance(tables,dict) and set(tables)==set(TABLES),'Export tables must be exactly: '+', '.join(TABLES))
    counts={}
    with transaction(db):
        require(all(db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]==0 for t in TABLES),'Restore needs an empty database; use a new --db path')
        for t in TABLES:
            columns=[r['name'] for r in db.execute('PRAGMA table_info('+t+')')]
            rows=tables[t]; require(isinstance(rows,list),t+' must be a list')
            for row in rows:
                require(isinstance(row,dict) and set(row)==set(columns),t+' rows must have exactly the columns: '+', '.join(columns))
                db.execute('INSERT INTO '+t+'('+','.join(columns)+') VALUES ('+','.join('?'*len(columns))+')',[row[c] for c in columns])
            counts[t]=len(rows)
        require(not db.execute('PRAGMA foreign_key_check').fetchall(),'Export has broken references')
    return {'status':'restored','rows':counts}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--db',required=True,help='path to the SQLite ledger file (created by init)')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init',help='Create the ledger database')
    reg=sub.add_parser('register',help='Register a document version'); reg.add_argument('--record',required=True,help=JSON_FILE.format('record')+'; see references/cli.md'); reg.add_argument('--file',help='path to the local source file, to compute its SHA-256'); reg.add_argument('--images-dir',help='Folder holding the images named in the record, to compute their hashes')
    planp=sub.add_parser('plan',help='Queue reading jobs for pages'); planp.add_argument('--doc',required=True,help='document ID'); planp.add_argument('--mode',choices=MODES,required=True,help='reading mode'); planp.add_argument('--pages',help='pages such as 5-8,40 (default: all pages)'); planp.add_argument('--batch-pages',type=int,default=2,help='pages per job (default 2)'); planp.add_argument('--tokens-per-page',type=int,required=True,help='estimated tokens per page, from actual usage'); planp.add_argument('--priority',type=int,default=50,help='higher runs first (default 50)'); planp.add_argument('--max-attempts',type=int,default=3,help='completed attempts per page and mode (default 3)'); planp.add_argument('--reread-reason',help='recorded reason that allows another attempt after full coverage')
    bp=sub.add_parser('budget',help='Record a host allowance window'); bp.add_argument('--id',required=True,help='allowance window ID'); bp.add_argument('--tokens',type=int,required=True,help='token allowance for the window'); bp.add_argument('--start',required=True,help='window start, ISO 8601 with time zone'); bp.add_argument('--end',required=True,help='window end, ISO 8601 with time zone')
    cp=sub.add_parser('claim',help='Claim the next fitting job'); cp.add_argument('--worker',required=True,help='worker ID'); cp.add_argument('--mode',choices=MODES,help='only claim jobs in this mode')
    fp=sub.add_parser('finish',help='Record the result of a claimed job'); fp.add_argument('--job',required=True,help='job ID returned by claim'); fp.add_argument('--worker',required=True,help='worker ID that claimed the job'); fp.add_argument('--result',required=True,help=JSON_FILE.format('result')+'; see references/cli.md')
    ip=sub.add_parser('import-run',help='Import a reading done outside the queue'); ip.add_argument('--doc',required=True,help='document ID'); ip.add_argument('--mode',choices=MODES,required=True,help='mode of the original reading'); ip.add_argument('--result',required=True,help=JSON_FILE.format('result')+' with metadata.external_run_id')
    sp=sub.add_parser('status',help='Show coverage for a document'); sp.add_argument('--doc',required=True,help='document ID')
    xp=sub.add_parser('export',help='Write a private JSON export'); xp.add_argument('--out',required=True,help='path of a new JSON file; an existing file is never overwritten')
    rp=sub.add_parser('restore',help='Rebuild an empty database from an export'); rp.add_argument('--from',dest='source',required=True,help='path to a JSON file written by export, or - to read it from stdin')
    can=sub.add_parser('cancel',help='Cancel a queued job'); can.add_argument('--job',required=True,help='queued job ID'); can.add_argument('--reason',required=True,help='recorded reason for cancelling')
    a=p.parse_args(); db=None
    try:
        db=connect(a.db,a.command in ('init','restore'))
        read=lambda f,flag='JSON file':read_json(f,flag)
        if a.command=='init': out={'status':'initialized','schema_version':2}
        elif a.command=='register': out=register(db,read(a.record,'--record'),a.file,a.images_dir)
        elif a.command=='plan': out=plan(db,a.doc,a.mode,a.pages,a.batch_pages,a.tokens_per_page,a.priority,a.max_attempts,a.reread_reason)
        elif a.command=='budget': out=budget(db,a.id,a.tokens,a.start,a.end)
        elif a.command=='claim': out=claim(db,a.worker,a.mode)
        elif a.command=='finish': out=finish(db,a.job,a.worker,read(a.result,'--result'))
        elif a.command=='import-run': out=import_history(db,a.doc,a.mode,read(a.result,'--result'))
        elif a.command=='cancel': out=cancel(db,a.job,a.reason)
        elif a.command=='status': out=status(db,a.doc)
        elif a.command=='restore': out=restore(db,read(a.source,'--from'))
        else:
            out=export_data(db)
            with Path(a.out).open('x',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False,indent=2); f.write('\n')
            out={'status':'exported','path':a.out,'private':True}
        print(json.dumps(out,ensure_ascii=False,indent=2)); return 0
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error) as e:
        print(json.dumps({'error':str(e)})); return 2
    finally:
        if db: db.close()

if __name__=='__main__': sys.exit(main())
