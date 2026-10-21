#!/usr/bin/env python3
"""Build one self-contained folder per skill under dist/skills/<name>/.

The source tree keeps a single copy of each shared file (for example
genealogy-mode/references/shared-contract.md), and plugin installs keep the
sibling folders, so relative links such as ../genealogy-mode/... work there.
A host that installs one skill on its own (claude.ai) has no siblings. This
build copies every file a skill links to from another skill into
shared/<other-skill>/... inside the bundle and rewrites the links to match.
It also drops frontmatter keys the Agent Skills spec does not allow (see
SPEC_KEYS), which claude.ai rejects on upload.

Each bundle is built by running BUNDLE_STEPS in order. A step takes a Bundle
and changes its folder in place, so later packaging rules (frontmatter, zips,
version metadata) are added as further steps without touching the others.

With --release it also writes the release assets to <out>/release/:
<skill>.zip for each skill (the skill folder at the zip root, as claude.ai
wants), genealogy-skills-claude-ai.zip holding all of them, the plugin as
genealogy-plugin.zip, and SHA256SUMS. Zips are reproducible: entries are
sorted and carry a fixed timestamp. check_release() validates the assets and
runs before SHA256SUMS is written.

Usage: python scripts/package_skills.py [--out dist] [--skill NAME ...] [--release]
"""
import argparse
import hashlib
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'skills'
SHARED = 'shared'
LINK = re.compile(r'(\[[^\]]*\]\()([^)\s]+)(\))')
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc')
# Frontmatter keys the Agent Skills spec allows. claude.ai rejects an upload
# with any other key. Source files keep host-specific keys such as
# disable-model-invocation (Claude Code and Cursor need it); bundles drop them.
DESCRIPTION_LIMIT = 200  # claude.ai; the spec allows 1024
COMBINED_ZIP = 'genealogy-skills-claude-ai.zip'
PLUGIN_ZIP = 'genealogy-plugin.zip'
PLUGIN_ROOT = 'genealogy'
# Tracked paths that make up the plugin for Antigravity, Claude Code, Codex, Cursor and Gemini.
# install.py is left out: it checks the full repository against manifest.json.
PLUGIN_PATHS = ('.agents', '.antigravity-plugin', '.claude-plugin', '.cursor-plugin', 'assets', 'commands', 'skills',
                'plugin.json', 'gemini-extension.json', 'GEMINI.md', 'genealogy.py',
                'README.md', 'INSTALL.md', 'CHANGELOG.md', 'LICENSE')
PLUGIN_REQUIRED = ('.antigravity-plugin/plugin.json', '.claude-plugin/plugin.json', '.claude-plugin/marketplace.json', '.cursor-plugin/plugin.json',
                   'plugin.json', 'gemini-extension.json', 'skills/genealogy-mode/SKILL.md')
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
SPEC_KEYS = ('name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility')

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
    dropped: list = field(default_factory=list)


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


def clean_frontmatter(bundle):
    """Drop top-level frontmatter keys outside SPEC_KEYS, with any indented lines under them."""
    skill_md = bundle.path / 'SKILL.md'
    text = skill_md.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise PackagingError(f'{bundle.skill}: SKILL.md has no frontmatter')
    _, head, body = text.split('---', 2)
    kept, dropping = [], False
    for line in head.strip('\n').splitlines():
        key = re.match(r'^([A-Za-z][\w-]*):', line)
        if key:
            dropping = key.group(1) not in SPEC_KEYS
            if dropping:
                bundle.dropped.append(key.group(1))
        if not dropping:
            kept.append(line)
    skill_md.write_text('---\n' + '\n'.join(kept) + '\n---' + body, encoding='utf-8')


def stamp_version(bundle):
    """Add metadata.version from .release-please-manifest.json, the one place release-please bumps.

    The source SKILL.md files carry no version: they are covered by manifest.json checksums, so a
    release-please bump inside them would leave manifest.json stale on every release PR.
    """
    skill_md = bundle.path / 'SKILL.md'
    _, head, body = skill_md.read_text(encoding='utf-8').split('---', 2)
    lines = head.strip('\n').splitlines()
    if any(re.match(r'^\s+version:', line) for line in lines):
        raise PackagingError(f'{bundle.skill}: metadata.version belongs in .release-please-manifest.json, not SKILL.md')
    stamp = f'  version: "{version()}"'
    if 'metadata:' in lines:
        lines.insert(lines.index('metadata:') + 1, stamp)
    else:
        lines += ['metadata:', stamp]
    skill_md.write_text('---\n' + '\n'.join(lines) + '\n---' + body, encoding='utf-8')


BUNDLE_STEPS = [copy_skill, make_self_contained, clean_frontmatter, stamp_version]


def write_zip(target, entries):
    """Write a reproducible zip from (archive name, bytes) pairs."""
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries):
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)


def folder_entries(folder, prefix):
    return [(f'{prefix}/{p.relative_to(folder).as_posix()}', p.read_bytes())
            for p in folder.rglob('*') if p.is_file()]


def tracked_files():
    """Files git tracks under PLUGIN_PATHS, relative to the repository root."""
    result = subprocess.run(['git', 'ls-files', '-z', '--', *PLUGIN_PATHS], cwd=ROOT,
                            capture_output=True, check=True)
    return sorted(p for p in result.stdout.decode('utf-8').split('\0') if p)


def skill_zips(out, release, report):
    names = []
    for bundle in report['bundles']:
        name = f"{bundle['skill']}.zip"
        write_zip(release / name, folder_entries(out / 'skills' / bundle['skill'], bundle['skill']))
        names.append(name)
    write_zip(release / COMBINED_ZIP, [(n, (release / n).read_bytes()) for n in names])
    return names + [COMBINED_ZIP]


def plugin_zip(out, release, report):
    write_zip(release / PLUGIN_ZIP, [(f'{PLUGIN_ROOT}/{rel}', (ROOT / rel).read_bytes()) for rel in tracked_files()])
    return [PLUGIN_ZIP]


# Each builder writes assets into the release folder and returns their names.
RELEASE_BUILDERS = [skill_zips, plugin_zip]


def parse_frontmatter(text):
    """Top-level frontmatter keys and their single-line values; enough for SKILL.md as written here."""
    if not text.startswith('---\n') or text.count('---') < 2:
        return None
    head = text.split('---', 2)[1]
    values = {}
    for line in head.splitlines():
        match = re.match(r'^([A-Za-z][\w-]*):\s*(.*)$', line)
        if match:
            raw = match.group(2).strip()
            values[match.group(1)] = json.loads(raw) if raw.startswith('"') else raw.strip("'")
    return values


def check_skill_zip(path, skill):
    problems = []
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        roots = {n.split('/', 1)[0] for n in names}
        if roots != {skill}:
            return [f'{path.name}: top level is {sorted(roots)}, expected {skill}/']
        front = parse_frontmatter(archive.read(f'{skill}/SKILL.md').decode('utf-8')) if f'{skill}/SKILL.md' in names else None
        if front is None:
            return [f'{path.name}: missing SKILL.md or frontmatter']
        extra = sorted(set(front) - set(SPEC_KEYS))
        if extra:
            problems.append(f'{path.name}: frontmatter keys outside the spec: {extra}')
        if front.get('name') != skill:
            problems.append(f'{path.name}: name {front.get("name")!r} does not match the folder')
        description = front.get('description', '')
        if not description or len(description) > DESCRIPTION_LIMIT or re.search('[<>]', description):
            problems.append(f'{path.name}: description is empty, over {DESCRIPTION_LIMIT} characters or has angle brackets')
        for doc in sorted(n for n in names if n.endswith('.md')):
            for target in LINK.findall(archive.read(doc).decode('utf-8')):
                link = target[1].partition('#')[0]
                if not link or not is_relative(link):
                    continue
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(doc), link))
                if not resolved.startswith(skill + '/') or (resolved not in names and not any(
                        n.startswith(resolved + '/') for n in names)):
                    problems.append(f'{path.name}: {doc} links to {link}, which is not in the zip')
    return problems


def check_release(release):
    """Validate the assets in a release folder. Returns a list of problems; empty means valid."""
    release = Path(release)
    problems = []
    skill_zips_found = sorted(p for p in release.glob('*.zip') if p.name not in (COMBINED_ZIP, PLUGIN_ZIP))
    expected = [f'{name}.zip' for name in skill_names()]
    if [p.name for p in skill_zips_found] != expected:
        problems.append(f'skill zips are {[p.name for p in skill_zips_found]}, expected {expected}')
    for path in skill_zips_found:
        problems.extend(check_skill_zip(path, path.stem))
    if (release / COMBINED_ZIP).is_file():
        with zipfile.ZipFile(release / COMBINED_ZIP) as archive:
            if sorted(archive.namelist()) != [p.name for p in skill_zips_found]:
                problems.append(f'{COMBINED_ZIP} does not hold exactly the skill zips')
            for path in skill_zips_found:
                if path.name in archive.namelist() and archive.read(path.name) != path.read_bytes():
                    problems.append(f'{COMBINED_ZIP}: {path.name} differs from the separate asset')
    else:
        problems.append(f'{COMBINED_ZIP} is missing')
    if (release / PLUGIN_ZIP).is_file():
        with zipfile.ZipFile(release / PLUGIN_ZIP) as archive:
            names = set(archive.namelist())
        missing = [rel for rel in PLUGIN_REQUIRED if f'{PLUGIN_ROOT}/{rel}' not in names]
        if missing:
            problems.append(f'{PLUGIN_ZIP} is missing {missing}')
    else:
        problems.append(f'{PLUGIN_ZIP} is missing')
    sums = release / 'SHA256SUMS'
    if sums.is_file():
        for line in sums.read_text(encoding='utf-8').splitlines():
            digest, _, name = line.partition('  ')
            if not (release / name).is_file() or sha256(release / name) != digest:
                problems.append(f'SHA256SUMS does not match {name}')
    return problems


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_release(out, report):
    release = out / 'release'
    if release.exists():
        shutil.rmtree(release)
    release.mkdir(parents=True)
    assets = []
    for builder in RELEASE_BUILDERS:
        assets.extend(builder(out, release, report))
    problems = check_release(release)
    if problems:
        raise PackagingError('release check failed: ' + '; '.join(problems))
    (release / 'SHA256SUMS').write_text(''.join(f'{sha256(release / n)}  {n}\n' for n in sorted(assets)), encoding='utf-8')
    return {'folder': str(release), 'assets': sorted(assets) + ['SHA256SUMS']}


def build(out, names=None, release=False):
    """Build bundles into out/skills/, and with release=True the assets into out/release/. Returns a report."""
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
        report['bundles'].append({'skill': name, 'shared': sorted(bundle.shared), 'links_rewritten': bundle.rewritten,
                                  'frontmatter_dropped': bundle.dropped})
    if release:
        if names != skill_names():
            raise PackagingError('a release needs every skill; drop --skill')
        report['release'] = build_release(out, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=str(ROOT / 'dist'), help='output folder (default: dist/)')
    parser.add_argument('--skill', action='append', help='build only this skill; repeat for more')
    parser.add_argument('--release', action='store_true', help='also write the release zips and SHA256SUMS')
    args = parser.parse_args()
    try:
        report = build(args.out, args.skill, release=args.release)
    except PackagingError as error:
        print(json.dumps({'error': str(error)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
