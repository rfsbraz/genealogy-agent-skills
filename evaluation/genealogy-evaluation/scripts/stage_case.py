#!/usr/bin/env python3
"""Stage public fixtures and optional runtime skills, excluding evaluation keys."""
import argparse
import json
from pathlib import Path
import shutil
import sys

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',required=True); p.add_argument('--out',required=True)
    p.add_argument('--skills-root',help='Optional sibling root containing installed skill folders')
    a=p.parse_args()
    try:
        base=Path(__file__).resolve().parents[1]/'assets/benchmark/public'
        src=base/a.case
        if src.parent!=base or not src.is_dir(): raise ValueError('Unknown or invalid case ID')
        dest=Path(a.out)
        if dest.exists(): raise ValueError('Output must not already exist')
        candidates=[]
        if a.skills_root:
            for folder in sorted(Path(a.skills_root).iterdir()):
                skill=folder/'SKILL.md'
                if not folder.is_dir() or not skill.is_file(): continue
                # Only the suite, including a host-renamed manuscript skill.
                lines=skill.read_text(encoding='utf-8').splitlines()
                name=next((line.split(':',1)[1].strip().strip('"\'') for line in lines if line.startswith('name:')),'')
                if name.startswith('genealogy-') and name!='genealogy-evaluation':
                    if any(x.is_symlink() for x in folder.rglob('*')): raise ValueError('Symlinks are not supported in skill staging')
                    candidates.append((folder,name))
        dest.mkdir(parents=True)
        shutil.copytree(src,dest/'inputs')
        for folder,name in candidates:
            shutil.copytree(folder,dest/'skills'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (dest/'STAGING-NOTICE.txt').write_text('Only public fixtures and runtime skills are staged. This directory is NOT a security sandbox. Run the agent with filesystem and network isolation supplied by the host. Keep evaluator files outside agent-visible mounts.\n')
        print(json.dumps({'path':str(dest),'case_id':a.case,'runtime_skills':len(candidates),'isolated':False}))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'error':str(e)})); return 2

if __name__=='__main__': sys.exit(main())
