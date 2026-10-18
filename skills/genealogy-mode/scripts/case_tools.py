#!/usr/bin/env python3
"""Portable case creation, hashing and core consistency checks. No network access."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gps_review import validate_reviews, evidence_digest

COLLECTIONS = ('questions persons mentions relationships events places sources citations observations hypotheses conclusions searches tasks repositories holdings correspondence changes').split()

def check_shape(value, schema, root, path='$'):
    errors=[]
    if '$ref' in schema:
        node=root
        for key in schema['$ref'][2:].split('/'): node=node[key]
        return check_shape(value,node,root,path)
    types={'string':lambda x:isinstance(x,str),'integer':lambda x:isinstance(x,int) and not isinstance(x,bool),'number':lambda x:isinstance(x,(int,float)) and not isinstance(x,bool),'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),'null':lambda x:x is None,'boolean':lambda x:isinstance(x,bool)}
    wanted=schema.get('type')
    if wanted:
        wanted=[wanted] if isinstance(wanted,str) else wanted
        if not any(types[t](value) for t in wanted): return [f'{path}: expected {wanted}']
    if 'const' in schema and value!=schema['const']: errors.append(f'{path}: must equal {schema["const"]!r}')
    if 'enum' in schema and value not in schema['enum']: errors.append(f'{path}: invalid value {value!r}')
    if isinstance(value,str) and len(value.strip())<schema.get('minLength',0): errors.append(f'{path}: empty string')
    if isinstance(value,(int,float)) and not isinstance(value,bool) and value<schema.get('minimum',float('-inf')): errors.append(f'{path}: below minimum')
    if isinstance(value,dict):
        if schema.get('additionalProperties') is False:
            for key in value.keys()-schema.get('properties',{}).keys(): errors.append(f'{path}.{key}: unexpected property')
        for k in schema.get('required',[]):
            if k not in value: errors.append(f'{path}.{k}: required')
        for k,s in schema.get('properties',{}).items():
            if k in value: errors += check_shape(value[k],s,root,f'{path}.{k}')
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0): errors.append(f'{path}: insufficient items')
        if schema.get('uniqueItems') and len({json.dumps(x,sort_keys=True) for x in value})!=len(value): errors.append(f'{path}: duplicate items')
        for i,x in enumerate(value): errors += check_shape(x,schema.get('items',{}),root,f'{path}[{i}]')
    return errors

def cycle_errors(graph,label):
    errors=[]; active=set(); done=set()
    def visit(n):
        if n in active:
            errors.append(f'{label}: cycle involving {n}'); return
        if n in done: return
        active.add(n)
        for child in graph.get(n,[]): visit(child)
        active.remove(n); done.add(n)
    for n in graph: visit(n)
    return errors

def validate_case(case, gps=False):
    schema=json.loads((ASSETS/'case.schema.json').read_text(encoding='utf-8'))
    errors=check_shape(case,schema,schema)
    if errors: return errors
    tables={name:{x['id']:x for x in case[name]} for name in COLLECTIONS}
    ids={}
    for name in COLLECTIONS:
        for row in case[name]:
            rid=row['id']
            if rid in ids: errors.append(f'duplicate ID {rid} in {ids[rid]} and {name}')
            ids[rid]=name
    def ref(value,collection,context):
        if value not in tables[collection]: errors.append(f'{context}: missing {collection} ID {value}')
    ref(case['active_question_id'],'questions','active_question_id')
    for name in ('mentions','citations','observations'):
        for row in case[name]: ref(row['source_id'],'sources',row['id'])
    for row in case['mentions']:
        if row.get('person_id'): ref(row['person_id'],'persons',row['id'])
    for row in case['observations']:
        if row.get('citation_id'):
            ref(row['citation_id'],'citations',row['id'])
            cit=tables['citations'].get(row['citation_id'])
            if cit and cit['source_id']!=row['source_id']: errors.append(f'{row["id"]}: citation/source mismatch')
        if row.get('subject_id') and row['subject_id'] not in tables['persons'] and row['subject_id'] not in tables['mentions']:
            errors.append(f'{row["id"]}: missing subject person/mention')
    superseded = {o['supersedes'] for o in case['observations'] if o.get('supersedes')}
    replacements = {}
    for row in case['observations']:
        old_id = row.get('supersedes')
        if old_id:
            ref(old_id, 'observations', row['id'])
            old = tables['observations'].get(old_id)
            if old and old['source_id'] != row['source_id']: errors.append(f'{row["id"]}: reread source mismatch')
            if old_id in replacements: errors.append(f'{old_id}: multiple replacement readings; reconcile explicitly')
            replacements[old_id] = row['id']
    errors += cycle_errors({o['id']: [o['supersedes']] if o.get('supersedes') else [] for o in case['observations']}, 'observation supersession')
    for row in case['sources']:
        for parent in row['derived_from']: ref(parent,'sources',row['id'])
    for name in ('hypotheses','conclusions','searches','tasks'):
        for row in case[name]: ref(row['question_id'],'questions',row['id'])
    for row in case['conclusions']:
        for oid in row['observation_ids']: ref(oid,'observations',row['id'])
        for cid in row['depends_on']: ref(cid,'conclusions',row['id'])
        if row['status'] in ('supported', 'source_supported') and not row['observation_ids']: errors.append(f'{row["id"]}: supported conclusion lacks observations')
        if row['status'] in ('supported', 'source_supported'):
            if set(row['observation_ids']) & superseded: errors.append(f'{row["id"]}: uses superseded reading')
            if row.get('review_required'): errors.append(f'{row["id"]}: reassessment still required')
        if row['status'] == 'source_supported':
            if case['schema_version'] != '1.2': errors.append(f'{row["id"]}: source_supported needs schema 1.2')
            assessment = row.get('evidence_assessment')
            if not assessment: errors.append(f'{row["id"]}: source support needs a scoped evidence assessment')
            else:
                try: date.fromisoformat(assessment['reviewed_on'])
                except ValueError: errors.append(f'{row["id"]}: assessment date must be YYYY-MM-DD')
                if any(c['material'] and not c['resolved'] for c in assessment['known_conflicts']):
                    errors.append(f'{row["id"]}: material conflict prevents source support')
            for oid in row['observation_ids']:
                obs = tables['observations'].get(oid, {})
                cit = tables['citations'].get(obs.get('citation_id'), {})
                if not cit.get('text', '').strip(): errors.append(f'{row["id"]}: source support needs full citations')
            for dep in row['depends_on']:
                if tables['conclusions'].get(dep, {}).get('status') not in ('supported', 'source_supported'):
                    errors.append(f'{row["id"]}: unresolved dependency {dep}')
    for row in case['hypotheses']:
        for key in ('support_ids','counterevidence_ids'):
            for oid in row.get(key,[]): ref(oid,'observations',row['id'])
    parents={}
    for row in case['relationships']:
        ref(row['from_person_id'],'persons',row['id']); ref(row['to_person_id'],'persons',row['id']); ref(row['conclusion_id'],'conclusions',row['id'])
        if row['from_person_id']==row['to_person_id']: errors.append(f'{row["id"]}: self relationship')
        conclusion=tables['conclusions'].get(row['conclusion_id'])
        if row['status']=='supported' and (not conclusion or conclusion['status']!='supported'): errors.append(f'{row["id"]}: supported relationship needs a supported conclusion')
        if row['status']=='source_supported' and (not conclusion or conclusion['status'] not in ('supported','source_supported')): errors.append(f'{row["id"]}: source-supported relationship needs an assessed conclusion')
        if row['status']=='supported' and row['type'] in ('parent','biological_parent'):
            parents.setdefault(row['from_person_id'],[]).append(row['to_person_id'])
    for row in case['events']:
        for oid in row['observation_ids']: ref(oid,'observations',row['id'])
        for pid in row.get('participant_ids',[]):
            if pid not in tables['persons'] and pid not in tables['mentions']: errors.append(f'{row["id"]}: missing event participant {pid}')
    for row in case['holdings']: ref(row['repository_id'],'repositories',row['id'])
    seen_requests=set()
    for row in case['correspondence']:
        if row['request_key'] in seen_requests: errors.append(f'{row["id"]}: duplicate correspondence request_key')
        seen_requests.add(row['request_key'])
        if row['status'] in ('sent','awaiting_reply') and not row.get('message_id'): errors.append(f'{row["id"]}: sent state needs actual message ID')
        if row['status'] in ('ready_authorized','sending','sent','awaiting_reply') and not row.get('authorization_ref'): errors.append(f'{row["id"]}: sending state needs an authorization reference')
    for row in case['changes']:
        if row['revision']>case['revision']: errors.append(f'{row["id"]}: change revision exceeds case revision')
    errors+=cycle_errors({s['id']:s['derived_from'] for s in case['sources']},'source derivation')
    errors+=cycle_errors({c['id']:c['depends_on'] for c in case['conclusions']},'conclusion dependency')
    errors+=cycle_errors({t['id']:t.get('depends_on',[]) for t in case['tasks']},'task dependency')
    for t in case['tasks']:
        for dep in t.get('depends_on',[]): ref(dep,'tasks',t['id'])
    errors+=cycle_errors(parents,'supported ancestry')
    if not errors:
        errors += validate_reviews(case, check_shape, required=gps or case['schema_version'] in ('1.1', '1.2'))
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    new=sub.add_parser('init'); new.add_argument('--case-id',required=True); new.add_argument('--question',required=True); new.add_argument('--out',required=True)
    val=sub.add_parser('validate'); val.add_argument('file'); val.add_argument('--gps',action='store_true',help='Audit legacy cases with the GPS gate too')
    digest=sub.add_parser('evidence-digest'); digest.add_argument('file')
    ha=sub.add_parser('hash-file'); ha.add_argument('file')
    args=p.parse_args()
    try:
        if args.command=='init':
            case=json.loads((ASSETS/'case-template.json').read_text(encoding='utf-8'))
            case['case_id']=args.case_id; case['goal']=args.question; case['questions'][0]['text']=args.question
            errors=validate_case(case)
            if errors: raise ValueError('; '.join(errors))
            target=Path(args.out); target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('x',encoding='utf-8') as f: json.dump(case,f,ensure_ascii=False,indent=2); f.write('\n')
            print(json.dumps({'status':'created','path':str(target),'case_id':case['case_id']}))
        elif args.command=='evidence-digest':
            print(evidence_digest(json.loads(Path(args.file).read_text(encoding='utf-8'))))
        elif args.command=='hash-file':
            digest=hashlib.sha256(); size=0
            with Path(args.file).open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''): digest.update(chunk); size+=len(chunk)
            print(json.dumps({'path':args.file,'sha256':digest.hexdigest(),'size_bytes':size}))
        else:
            case=json.loads(Path(args.file).read_text(encoding='utf-8'))
            errors=validate_case(case,gps=args.gps)
            print(json.dumps({'valid':not errors,'errors':errors,'gps_required':args.gps or case['schema_version'] in ('1.1', '1.2'),'scope':'structure and documented review; not historical truth or GPS certification'},ensure_ascii=False,indent=2))
            return 1 if errors else 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'error':str(e)})); return 2
    return 0

if __name__=='__main__': sys.exit(main())
