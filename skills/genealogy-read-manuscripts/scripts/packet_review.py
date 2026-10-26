"""Record a visual preflight and release only an unchanged, passed packet set."""
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import shutil
import socket
import tempfile

LOG='preflight-log.jsonl'
REPLACED='preflight-replaced'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_file(root, relative):
    path=Path(relative)
    if path.is_absolute() or '..' in path.parts:raise ValueError('Packet path escapes its root.')
    resolved=(root/path).resolve()
    if not resolved.is_relative_to(root.resolve()) or (root/path).is_symlink():raise ValueError('Unsafe packet file.')
    return resolved


def require_schema(manifest):
    if manifest.get('schema_version')!='1.2':raise ValueError('Dispatch requires packet schema 1.2; rebuild older packets.')


def fingerprint(root, manifest):
    require_schema(manifest)
    for name,expected in manifest['inventory'].items():
        path=safe_file(root,name)
        if not path.is_file() or sha(path)!=expected:raise ValueError('Packet changed or missing: '+name)
    return manifest_digest(manifest)


def manifest_digest(manifest):return hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()


SOURCE_QUALITY=('adequate_for_attempt','needs_better_source')


def checks_for(region):
    """Boolean checks for one review region. A line-start target has no anchor to confirm."""
    middle='line_start_correct' if region.get('target_at_line_start') else 'anchor_correct'
    return ('source_page_correct','target_complete',middle,'views_usable')


def template(root, manifest):
    regions=[]
    for row in manifest['review_regions']:
        region={'region_id':row['region_id'],'inspected_files':[],
            'required_files':row['required_files'],'source_page_correct':None,
            'target_complete':None,'anchor_correct':None,'views_usable':None,
            'source_quality':' | '.join(SOURCE_QUALITY),'notes':''}
        if row.get('target_at_line_start'):region['line_start_correct']=None
        regions.append(region)
    return {'schema_version':'1.0','packet_digest':fingerprint(root,manifest),
        'reviewed_by':'','reviewed_at':'','regions':regions}


def assess(root, manifest, record):
    if not isinstance(record,dict):raise ValueError('Preflight record must be an object.')
    current=fingerprint(root,manifest)
    if record.get('packet_digest')!=current:raise ValueError('Stale preflight: packet digest does not match.')
    if not isinstance(record.get('reviewed_by'),str) or not record['reviewed_by'].strip():raise ValueError('Record the reviewing operator/context.')
    try:when=datetime.fromisoformat(record['reviewed_at'].replace('Z','+00:00'))
    except (KeyError,TypeError,ValueError,AttributeError) as exc:raise ValueError('Use an ISO reviewed_at timestamp with timezone.') from exc
    if when.tzinfo is None:raise ValueError('reviewed_at needs a timezone.')
    regions=record.get('regions')
    if not isinstance(regions,list) or any(not isinstance(r,dict) for r in regions):raise ValueError('regions must be review objects.')
    expected={r['region_id']:r for r in manifest['review_regions']}
    ids=[r.get('region_id') for r in regions]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):raise ValueError('Review every target exactly once.')
    blocked=[]
    for row in regions:
        files=row.get('inspected_files')
        if not isinstance(files,list) or any(not isinstance(p,str) for p in files):raise ValueError('Record exact inspected file paths.')
        if not set(expected[row['region_id']]['required_files']).issubset(files):raise ValueError('Missing required visual checks for '+row['region_id'])
        if any(p not in manifest['inventory'] for p in files):raise ValueError('Inspection names an unknown packet file.')
        checks=checks_for(expected[row['region_id']])
        if any(type(row.get(k)) is not bool for k in checks):raise ValueError('Complete each boolean visual check for '+row['region_id']+': '+', '.join(checks)+'.')
        if 'line_start_correct' in checks and row.get('anchor_correct') is not None:raise ValueError('Leave anchor_correct null for line-start target '+row['region_id']+'; record line_start_correct instead.')
        if row.get('source_quality') not in SOURCE_QUALITY:raise ValueError('Record source quality for '+row['region_id']+' as adequate_for_attempt or needs_better_source.')
        if not isinstance(row.get('notes'),str) or not row['notes'].strip():raise ValueError('Record a concrete inspection note.')
        if not all(row[k] for k in checks) or row['source_quality']=='needs_better_source':blocked.append(row['region_id'])
    return {'status':'blocked' if blocked else 'passed','packet_digest':current,
            'blocked_regions':blocked,'record':record,
            'limits':'This enforces a recorded operator assessment and immutable inputs, not proof that pixels were actually inspected or targets correctly understood.'}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def digest_of(value):return hashlib.sha256(canonical(value).encode()).hexdigest()


def start_log(root, manifest):
    """Open the append-only review log at build time, so a deleted log cannot pass as a fresh packet."""
    entry={'event':'built','sequence':0,'previous':None,'packet_id':manifest['packet_id'],'packet_digest':fingerprint(root,manifest)}
    with (Path(root)/LOG).open('x',encoding='utf-8') as out:out.write(canonical(entry)+'\n')


def read_log(root, manifest):
    require_schema(manifest)
    path=Path(root)/LOG
    if not path.is_file() or path.is_symlink():raise ValueError('Preflight review log is missing; rebuild the packet set in a fresh directory.')
    entries=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    previous=None
    for n,entry in enumerate(entries):
        if entry.get('sequence')!=n or entry.get('previous')!=previous:raise ValueError('Preflight review log was edited; rebuild the packet set in a fresh directory.')
        previous=digest_of(entry)
    if not entries or entries[0].get('event')!='built' or entries[0].get('packet_digest')!=manifest_digest(manifest):
        raise ValueError('Preflight review log does not belong to this packet set; rebuild it in a fresh directory.')
    for entry in entries[1:]:
        if entry.get('event')!='review' or entry.get('review_digest')!=review_digest(entry):
            raise ValueError('Preflight review log was edited; rebuild the packet set in a fresh directory.')
    return entries


def review_digest(entry):
    """Bind a review to its answers, its reviewer and the exact bytes of the files it inspected."""
    return digest_of({k:entry.get(k) for k in ('packet_digest','reviewer','recorded_by','recorded_at','input_hashes','result')})


def operator():
    try:user=getpass.getuser()
    except (KeyError,OSError):user='unknown'
    return user+'@'+socket.gethostname()


def record_preflight(manifest_path, record):
    """Save a review. A replaced review stays in the log and in preflight-replaced/, never overwritten."""
    manifest_path=Path(manifest_path);root=manifest_path.parent
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    entries=read_log(root,manifest)
    result=assess(root,manifest,record)
    inspected=sorted({p for row in record['regions'] for p in row['inspected_files']})
    entry={'event':'review','sequence':len(entries),'previous':digest_of(entries[-1]),
           'packet_digest':result['packet_digest'],'reviewer':record['reviewed_by'],'recorded_by':operator(),
           'recorded_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
           'input_hashes':{name:sha(safe_file(root,name)) for name in inspected},'result':result}
    entry['review_digest']=review_digest(entry)
    previous=[e for e in entries if e['event']=='review']
    receipt=root/'preflight.json'
    if receipt.exists():
        kept=root/REPLACED;kept.mkdir(exist_ok=True)
        receipt.rename(kept/('preflight-'+str(len(list(kept.iterdir()))+1).zfill(3)+'.json'))
    with (root/LOG).open('a',encoding='utf-8') as out:out.write(canonical(entry)+'\n')
    saved=dict(result,review_digest=entry['review_digest'],sequence=entry['sequence'],
               replaces=previous[-1]['review_digest'] if previous else None)
    with receipt.open('x',encoding='utf-8') as out:json.dump(saved,out,ensure_ascii=False,indent=2);out.write('\n')
    return saved


def dispatch(manifest_path):
    manifest_path=Path(manifest_path);root=manifest_path.parent
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    entries=read_log(root,manifest)
    reviews=[e for e in entries if e['event']=='review']
    receipt=root/'preflight.json'
    if not receipt.is_file() or not reviews:raise ValueError('Dispatch blocked: record a completed preflight first.')
    latest=reviews[-1]
    stored=json.loads(receipt.read_text(encoding='utf-8'))
    if not isinstance(stored,dict) or stored.get('review_digest')!=latest['review_digest'] or stored.get('record')!=latest['result']['record']:
        raise ValueError('Dispatch blocked: preflight.json does not match the review log. Record a new review with record-preflight.')
    for name,expected in latest['input_hashes'].items():
        path=safe_file(root,name)
        if not path.is_file() or sha(path)!=expected:raise ValueError('Packet changed since review: '+name)
    result=assess(root,manifest,latest['result']['record'])
    if result['status']!='passed':raise ValueError('Dispatch blocked: crop/display/source-quality check failed.')
    out=root/'dispatch'
    if out.exists():raise ValueError('Dispatch already exists; use the recorded task paths or build a new packet set.')
    stage=Path(tempfile.mkdtemp(prefix='dispatch.',dir=root))
    tasks=[]
    try:
        for method,packet in manifest['packets'].items():
            source=safe_file(root,packet['prompt']).parent
            destination=stage/source.name;destination.mkdir();(destination/'work').mkdir()
            # Copy only frozen input files; never include stray reports or private work.
            for name,expected in manifest['inventory'].items():
                file=safe_file(root,name)
                if file.parent==source:
                    shutil.copyfile(file,destination/file.name)
                    if sha(destination/file.name)!=expected:raise ValueError('Input changed during dispatch.')
            (destination/'dispatch-receipt.json').write_text(json.dumps({'packet_id':manifest['packet_id'],'method_id':method,'packet_digest':result['packet_digest'],'preflight':'passed','review_digest':latest['review_digest'],'replaced_reviews':len(reviews)-1},indent=2)+'\n',encoding='utf-8')
            tasks.append({'method_id':method,'prompt':str((out/source.name/'prompt.md').resolve()),
                          'inputs':str((out/source.name/'inputs.json').resolve())})
        fingerprint(root,manifest)
        (stage/'dispatch.json').write_text(json.dumps({'packet_digest':result['packet_digest'],'tasks':tasks},indent=2)+'\n',encoding='utf-8')
        stage.rename(out)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return {'status':'ready','packet_digest':result['packet_digest'],'tasks':tasks,
            'instruction':'Give each fresh context only its own prompt path. This helper releases inputs; it does not invoke models.'}
