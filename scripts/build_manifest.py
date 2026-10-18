#!/usr/bin/env python3
"""Regenerate manifest.json, or with --check fail when it is stale.

The version comes from .release-please-manifest.json, the single source that
release-please bumps, so a release PR keeps manifest.json current.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RELEASE_MANIFEST = '.release-please-manifest.json'
SCOPE_FILES = ('install.py', 'validate_package.py', 'genealogy.py')
SCOPE_DIRS = ('skills', 'evaluation', 'tests')
STATIC = {
    'suite': 'genealogy-agent-skills',
    'reused_unchanged': [],
    'runtime': 'Python 3.10+; local helpers only. Models, quotas and timers supplied by host.',
}


def covered_files(root):
    paths = [root / name for name in SCOPE_FILES]
    for folder in SCOPE_DIRS:
        if (root / folder).is_dir():
            paths.extend((root / folder).rglob('*'))
    files = [p for p in paths if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def build(root, version):
    files = {}
    for path in covered_files(root):
        data = path.read_bytes()
        files[path.relative_to(root).as_posix()] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    skill_count = sum(len(list((root / folder).glob('*/SKILL.md'))) for folder in ('skills', 'evaluation'))
    return {
        'suite': STATIC['suite'],
        'version': version,
        'skill_count': skill_count,
        'reused_unchanged': STATIC['reused_unchanged'],
        'runtime': STATIC['runtime'],
        'files': files,
    }


def render(manifest):
    return json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='exit 1 if manifest.json is out of date')
    args = parser.parse_args()
    target = ROOT / 'manifest.json'
    current = target.read_text(encoding='utf-8') if target.exists() else ''
    version = json.loads((ROOT / RELEASE_MANIFEST).read_text(encoding='utf-8'))['.']
    fresh = render(build(ROOT, version))
    if args.check:
        if fresh != current:
            print('manifest.json is stale; run python scripts/build_manifest.py')
            return 1
        print('manifest.json is up to date')
        return 0
    target.write_text(fresh, encoding='utf-8')
    print('wrote manifest.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
