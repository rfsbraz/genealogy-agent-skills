#!/usr/bin/env python3
"""Preview or install sibling skill directories; never overwrite conflicting skills.

The maintainer-only evaluation skill is installed only with --include-evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from validate_package import validate

def declared_name(folder):
    file=folder/'SKILL.md'
    if not file.is_file(): return None
    parts=file.read_text(encoding='utf-8').split('---',2)
    if len(parts)<3: return None
    return next((x.split(':',1)[1].strip().strip('"\'') for x in parts[1].splitlines() if x.startswith('name:')),None)

def fingerprint(folder):
    result={}
    for p in folder.rglob('*'):
        if '__pycache__' in p.parts or p.suffix=='.pyc': continue
        if p.is_symlink(): raise ValueError('Symlinks are not supported: '+str(p))
        if p.is_file(): result[p.relative_to(folder).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dest',required=True); p.add_argument('--apply',action='store_true')
    p.add_argument('--include-evaluation',action='store_true',help='also install the maintainer-only evaluation skill from evaluation/')
    args=p.parse_args(); created=[]
    try:
        root=Path(__file__).resolve().parent
        report=validate(root)
        if not report['valid']: raise ValueError('Package validation failed: '+'; '.join(report['errors']))
        dest=Path(args.dest).expanduser().resolve()
        if dest.exists() and not dest.is_dir(): raise ValueError('Destination is not a directory')
        existing={}
        if dest.exists():
            for folder in dest.iterdir():
                if folder.is_dir():
                    name=declared_name(folder)
                    if name: existing.setdefault(name,[]).append(folder)
        plan=[]
        sources=sorted((root/'skills').iterdir())
        if args.include_evaluation and (root/'evaluation').is_dir(): sources+=sorted((root/'evaluation').iterdir())
        for source in sources:
            if not source.is_dir(): continue
            name=declared_name(source)
            matches=existing.get(name,[])
            if len(matches)>1: raise ValueError('Duplicate installed skill names: '+name)
            target=matches[0] if matches else dest/source.name
            if target.exists():
                if target.is_dir() and fingerprint(target)==fingerprint(source): action='skip_identical'
                else: raise ValueError('Conflicting existing path; no changes made: '+str(target))
            else: action='install'
            plan.append((source,target,action))
        if args.apply:
            dest.mkdir(parents=True,exist_ok=True)
            for source,target,action in plan:
                if action=='install':
                    target.mkdir(); created.append(target)
                    shutil.copytree(source,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        print(json.dumps({'applied':args.apply,'actions':[{'skill':declared_name(s),'action':a,'path':str(t)} for s,t,a in plan]},indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        for target in reversed(created): shutil.rmtree(target)
        print(json.dumps({'error':str(e),'created_skill_directories_rolled_back':len(created)})); return 2

if __name__=='__main__': sys.exit(main())
