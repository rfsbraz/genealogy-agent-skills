#!/usr/bin/env python3
"""Verify package inventory and checksums; no network or agent execution."""
from pathlib import Path
import hashlib
import json
import sys

# Only these paths are covered by manifest.json; repo files such as README, LICENSE and docs/ are not.
SCOPE_DIRS=('skills','evaluation','tests')

def validate(root):
    errors=[]
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    expected=manifest['files']
    candidates=[root/'install.py',root/'validate_package.py',root/'genealogy.py']
    for folder in SCOPE_DIRS:
        if (root/folder).is_dir(): candidates.extend((root/folder).rglob('*'))
    actual={p.relative_to(root).as_posix():p for p in candidates if (p.is_file() or p.is_symlink()) and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    for rel in sorted(set(expected)-set(actual)): errors.append('Missing: '+rel)
    for rel in sorted(set(actual)-set(expected)): errors.append('Unexpected: '+rel)
    for rel,p in actual.items():
        if p.is_symlink(): errors.append('Symlink: '+rel)
        if rel in expected and hashlib.sha256(p.read_bytes()).hexdigest()!=expected[rel]['sha256']: errors.append('Hash mismatch: '+rel)
    names=[]
    for skill in [s for folder in ('skills','evaluation') for s in (root/folder).glob('*/SKILL.md')]:
        front=skill.read_text(encoding='utf-8').split('---',2)
        if len(front)<3: errors.append('Invalid frontmatter: '+str(skill)); continue
        name=next((s.split(':',1)[1].strip().strip('"\'') for s in front[1].splitlines() if s.startswith('name:')),None)
        if not name: errors.append('Missing skill name: '+str(skill)); continue
        names.append(name)
    if len(names)!=manifest['skill_count'] or len(set(names))!=len(names): errors.append('Skill count or duplicate name mismatch')
    return {'valid':not errors,'skill_count':len(names),'file_count':len(actual),'errors':errors}

if __name__=='__main__':
    try:
        report=validate(Path(__file__).resolve().parent)
        print(json.dumps(report,indent=2)); sys.exit(0 if report['valid'] else 1)
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'error':str(e)})); sys.exit(2)
