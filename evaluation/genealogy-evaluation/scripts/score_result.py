#!/usr/bin/env python3
"""Score synthetic starter decisions. Historical validity needs separate review."""
import argparse
import json
from pathlib import Path
import sys

def pointer(obj, path):
    if not path.startswith('/'):
        raise ValueError('Assertion path must be a JSON pointer')
    for part in path[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        obj=obj[int(part)] if isinstance(obj,list) else obj[part]
    return obj

def score(result, gold, trace=None):
    if not isinstance(result,dict) or not isinstance(gold,dict):
        raise ValueError('Result and gold must be JSON objects')
    checks=[]
    def check(name,passed,critical=False,detail=None):
        checks.append({'check':name,'passed':bool(passed),'critical':critical,'detail':detail})
    check('case_id',result.get('case_id')==gold['case_id'])
    for item in gold['assertions']:
        if item['op']!='equals': raise ValueError('Unsupported grader operation')
        try:
            value=pointer(result,item['path'])
            # JSON equality must distinguish booleans from integers.
            passed=json.dumps(value,sort_keys=True)==json.dumps(item['expected'],sort_keys=True)
            detail={'observed':value}
        except (KeyError,IndexError,TypeError,ValueError):
            passed=False; detail={'missing':True}
        check(item['path'],passed,item.get('critical',False),detail)
    evidence=result.get('evidence',{})
    allowed=set(gold['allowed_source_ids'])
    for field in gold['evidence_fields']:
        refs=evidence.get(field) if isinstance(evidence,dict) else None
        valid=isinstance(refs,list) and bool(refs) and all(isinstance(x,str) and x in allowed for x in refs)
        check('evidence_refs:'+field,valid,True)
    check('limitations_shape',isinstance(result.get('limitations'),list) and all(isinstance(x,str) for x in result.get('limitations',[])))
    trace_status='not_required'
    policy=gold.get('trace_policy')
    if policy is not None:
        trace_status='missing'
        if trace is not None:
            if not isinstance(trace,dict) or not isinstance(trace.get('events'),list): raise ValueError('Trace must contain an events list')
            valid=trace.get('case_id')==gold['case_id'] and trace.get('complete') is True and trace.get('producer')=='harness'
            for e in trace['events']:
                valid=valid and isinstance(e,dict) and isinstance(e.get('operation'),str)
            check('trace_envelope',valid,True)
            if valid:
                ops=[e['operation'] for e in trace['events']]
                for op in policy['forbidden_operations']: check('forbidden:'+op,op not in ops,True)
                for op in policy['required_operations']: check('required:'+op,op in ops)
                trace_status='checked'
            else: trace_status='invalid'
    critical=[c['check'] for c in checks if c['critical'] and not c['passed']]
    passed=sum(c['passed'] for c in checks)
    all_passed=passed==len(checks)
    status='fail' if not all_passed else ('unverified' if trace_status in ('missing','invalid') else 'pass')
    return {'case_id':gold['case_id'],'status':status,'checks_passed':passed,'checks_total':len(checks),
            'check_fraction':passed/len(checks),'critical_failures':critical,'trace_status':trace_status,'checks':checks,
            'limits':'Checks decision values and reference IDs, not actual citation support or historical truth. Trace integrity is the host responsibility.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--result',required=True); p.add_argument('--gold',required=True)
    p.add_argument('--trace'); p.add_argument('--out')
    a=p.parse_args()
    try:
        read=lambda path:json.loads(Path(path).read_text(encoding='utf-8'))
        report=score(read(a.result),read(a.gold),read(a.trace) if a.trace else None)
        rendered=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
        if a.out:
            with Path(a.out).open('x',encoding='utf-8') as f: f.write(rendered)
        print(rendered,end='')
        return 0 if report['status']=='pass' else (3 if report['status']=='unverified' else 1)
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'error':str(e)})); return 2

if __name__=='__main__': sys.exit(main())
