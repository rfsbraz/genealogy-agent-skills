#!/usr/bin/env python3
"""Build one self-contained folder per skill under dist/skills/<name>/.

The source tree keeps a single copy of each shared file (for example
genealogy-mode/references/shared-contract.md), and plugin installs keep the
sibling folders, so relative links such as ../genealogy-mode/... work there.
A host that installs one skill on its own (claude.ai) has no siblings. This
build copies every file a skill links to from another skill into
shared/<other-skill>/... inside the bundle and rewrites the links to match.

Each bundle is built by running BUNDLE_STEPS in order. A step takes a Bundle
and changes its folder in place, so later packaging rules (frontmatter, zips,
version metadata) are added as further steps without touching the others.

Usage: python scripts/package_skills.py [--out dist] [--skill NAME ...]
"""
import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'skills'
SHARED = 'shared'
LINK = re.compile(r'(\[[^\]]*\]\()([^)\s]+)(\))')
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc')

# Files a skill uses from another skill that are not Markdown links, such as
# helper modules a script imports. Paths are relative to skills/.
EXTRA_SHARED = {
    'genealogy-narrative': ['genealogy-mode/scripts/case_tools.py',
                            'genealogy-mode/scripts/gps_review.py',
                            'genealogy-mode/assets'],
}


class PackagingError(Exception):
    pass


@dataclass
class Bundle:
    skill: str
    path: Path
    shared: list = field(default_factory=list)
    rewritten: int = 0


def version():
    return json.loads((ROOT / '.release-please-manifest.json').read_text(encoding='utf-8'))['.']


def skill_names():
    return sorted(p.name for p in SKILLS.iterdir() if (p / 'SKILL.md').is_file())


def is_relative(target):
    return not (re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I) or target.startswith(('#', '/')))


def copy_skill(bundle):
    shutil.copytree(SKILLS / bundle.skill, bundle.path, ignore=IGNORE)


def place(bundle, source_rel):
    """Bundle path for a file given by its path relative to skills/."""
    owner, _, rest = source_rel.partition('/')
    if owner == bundle.skill:
        return bundle.path / rest
    return bundle.path / SHARED / owner / rest


def vendor(bundle, source_rel):
    """Copy skills/<source_rel> into the bundle once. Returns its bundle path."""
    source = SKILLS / source_rel
    target = place(bundle, source_rel)
    if not source.exists():
        raise PackagingError(f'{bundle.skill}: {source_rel} does not exist')
    if target.exists():
        return target, False
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=IGNORE)
    else:
        shutil.copy2(source, target)
    bundle.shared.append(source_rel)
    return target, True


def origin(bundle, path):
    """Path relative to skills/ that a bundle file was copied from."""
    rel = path.relative_to(bundle.path).as_posix()
    if rel.startswith(SHARED + '/'):
        return rel[len(SHARED) + 1:]
    return f'{bundle.skill}/{rel}'


def make_self_contained(bundle):
    """Copy linked files from other skills into the bundle and rewrite the links."""
    for source_rel in EXTRA_SHARED.get(bundle.skill, []):
        vendor(bundle, source_rel)
    queue = sorted(bundle.path.rglob('*.md'))
    seen = set()
    while queue:
        doc = queue.pop(0)
        if doc in seen:
            continue
        seen.add(doc)
        doc_origin = posixpath.dirname(origin(bundle, doc))

        def fix(match):
            target = match.group(2)
            if not is_relative(target):
                return match.group(0)
            path, hash_, anchor = target.partition('#')
            if not path:
                return match.group(0)
            source_rel = posixpath.normpath(posixpath.join(doc_origin, path))
            if source_rel.startswith('../'):
                raise PackagingError(f'{bundle.skill}: {doc.name} links outside skills/: {target}')
            dest, added = vendor(bundle, source_rel)
            if added and dest.is_file() and dest.suffix == '.md':
                queue.append(dest)
            elif added and dest.is_dir():
                queue.extend(sorted(dest.rglob('*.md')))
            new = os.path.relpath(dest, doc.parent).replace(os.sep, '/') + hash_ + anchor
            if new == target:
                return match.group(0)
            bundle.rewritten += 1
            return match.group(1) + new + match.group(3)

        text = doc.read_text(encoding='utf-8')
        fixed = LINK.sub(fix, text)
        if fixed != text:
            doc.write_text(fixed, encoding='utf-8')


BUNDLE_STEPS = [copy_skill, make_self_contained]


def build(out, names=None):
    """Build bundles into out/skills/. Returns a JSON-ready report."""
    out = Path(out)
    root = out / 'skills'
    names = names or skill_names()
    unknown = sorted(set(names) - set(skill_names()))
    if unknown:
        raise PackagingError('unknown skills: ' + ', '.join(unknown))
    report = {'version': version(), 'out': str(out), 'bundles': []}
    for name in names:
        bundle = Bundle(name, root / name)
        if bundle.path.exists():
            shutil.rmtree(bundle.path)
        bundle.path.parent.mkdir(parents=True, exist_ok=True)
        for step in BUNDLE_STEPS:
            step(bundle)
        report['bundles'].append({'skill': name, 'shared': sorted(bundle.shared), 'links_rewritten': bundle.rewritten})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=str(ROOT / 'dist'), help='output folder (default: dist/)')
    parser.add_argument('--skill', action='append', help='build only this skill; repeat for more')
    args = parser.parse_args()
    try:
        report = build(args.out, args.skill)
    except PackagingError as error:
        print(json.dumps({'error': str(error)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
