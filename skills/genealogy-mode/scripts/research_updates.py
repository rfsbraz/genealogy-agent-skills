#!/usr/bin/env python3
"""Append corrected readings and generate private repository views. No model/network calls."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from case_tools import validate_case


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def current_observations(case):
    replaced = {o['supersedes'] for o in case['observations'] if o.get('supersedes')}
    return [o for o in case['observations'] if o['id'] not in replaced]


def external_run(reading):
    """Return the reading's external run reference, marked as external, or None.

    Use it only when the host's own record holds the run and no queue run exists.
    Extra keys are kept so hosts can add fields later."""
    if 'external_run' not in reading:
        return None
    ref = reading['external_run']
    if not isinstance(ref, dict) or not isinstance(ref.get('ref'), str) or not ref['ref'].strip():
        raise ValueError('external_run must be an object with a nonempty ref.')
    if ref.get('kind', 'external') != 'external':
        raise ValueError('external_run.kind must be external.')
    if reading.get('processing_run_id'):
        raise ValueError('Give either processing_run_id or external_run, not both.')
    return {'kind': 'external', **{k: v for k, v in ref.items() if k != 'kind'}}


def apply_reread(case, old_id, reading, reason, actor, expected_revision):
    """The new observation ID is the idempotency key. Never rewrite old text."""
    if not reason.strip() or not actor.strip():
        raise ValueError('A specific correction reason and actual actor are required.')
    request = {'old_id': old_id, 'reading': reading, 'reason': reason, 'actor': actor}
    token = fingerprint(request)
    for change in case['changes']:
        if change.get('reread_id') == reading['id']:
            if change.get('input_digest') != token:
                raise ValueError('Reading ID reused with different input; use a new ID.')
            return copy.deepcopy(case), False
    if case['revision'] != expected_revision:
        raise ValueError('Revision changed; reload and reconcile before retrying.')
    old = next((o for o in current_observations(case) if o['id'] == old_id), None)
    if old is None:
        raise ValueError('Old observation is missing or already superseded.')
    if reading.get('source_id') != old['source_id']:
        raise ValueError('A reread must refer to the same source; record another source separately.')
    if reading.get('supersedes', old_id) != old_id:
        raise ValueError('Conflicting supersedes ID.')
    if not reading.get('citation_id'):
        raise ValueError('New reading needs citation_id.')
    external = external_run(reading)
    if external is None and not reading.get('processing_run_id'):
        raise ValueError('New reading needs the actual processing_run_id, or an external_run from the host record when no queue run exists.')
    if external is None and reading.get('processing_run_id') == old.get('processing_run_id'):
        raise ValueError('A reread needs a new processing run; retain the earlier run.')
    if external is not None and external['ref'] == (old.get('external_run') or {}).get('ref'):
        raise ValueError('A reread needs a new external run reference; retain the earlier one.')
    new = copy.deepcopy(reading)
    if external is not None:
        new['external_run'] = external
    new['supersedes'] = old_id
    new['revision_reason'] = reason
    result = copy.deepcopy(case)
    result['schema_version'] = '1.2'
    result['observations'].append(new)
    direct = {c['id'] for c in result['conclusions'] if old_id in c['observation_ids']}
    affected = set(direct)
    while True:
        expanded = affected | {c['id'] for c in result['conclusions'] if set(c['depends_on']) & affected}
        if expanded == affected:
            break
        affected = expanded
    # Ready reviews use a case-wide digest. Preserve them before invalidating;
    # distinguish global review refresh from claims actually affected by the reading.
    refresh = {c['id'] for c in result['conclusions']
               if c.get('gps_review', {}).get('decision') == 'ready'}
    impacted = affected | refresh
    while True:
        expanded = impacted | {c['id'] for c in result['conclusions'] if set(c['depends_on']) & impacted}
        if expanded == impacted:
            break
        impacted = expanded
    before = {'conclusions': [], 'relationships': [], 'events': []}
    for c in result['conclusions']:
        if c['id'] not in impacted:
            continue
        before['conclusions'].append(copy.deepcopy(c))
        c.pop('gps_review', None)
        if c['status'] == 'superseded':
            continue
        c.pop('evidence_assessment', None)
        c['status'] = 'provisional'
        c['review_required'] = True
        c['review_reason'] = ('Changed reading or dependency' if c['id'] in affected
                              else 'Case-wide GPS evidence digest changed')
    for rel in result['relationships']:
        if rel['conclusion_id'] in impacted and rel['status'] != 'superseded':
            before['relationships'].append(copy.deepcopy(rel))
            rel['status'] = 'provisional'
            rel['review_required'] = True
    for event in result['events']:
        if old_id in event['observation_ids']:
            before['events'].append(copy.deepcopy(event))
            event['review_required'] = True
    result['revision'] += 1
    result['changes'].append({'id': 'REREAD-' + new['id'], 'revision': result['revision'],
        'reason': reason, 'actor': actor, 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'affected_ids': sorted({old_id, new['id']} | impacted | {r['id'] for r in before['relationships']}
                               | {e['id'] for e in before['events']}),
        'reread_id': new['id'], 'input_digest': token, 'input': request,
        'supersedes': old_id, 'before': before, 'direct_conclusion_ids': sorted(direct),
        'dependent_conclusion_ids': sorted(affected - direct), 'gps_refresh_ids': sorted(impacted - affected)})
    if external is not None:
        result['changes'][-1]['external_run'] = copy.deepcopy(external)
    result['checkpoint']['next_action'] = 'Reassess corrected reading ' + new['id'] + ' and flagged dependencies; regenerate views.'
    errors = validate_case(result, gps=True)
    if errors:
        raise ValueError('; '.join(errors))
    return result, True


def save_reread(path, **kwargs):
    path = Path(path).resolve()
    lock = path.with_name(path.name + '.lock')
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    temporary = None
    try:
        os.close(fd)
        case = json.loads(path.read_text(encoding='utf-8'))
        result, changed = apply_reread(case, **kwargs)
        if changed:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix=path.name + '.', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(result, handle, ensure_ascii=False, indent=2)
                handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
        return result, changed
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
        lock.unlink()


def projection(case, mapping=None, tree=None):
    """Pure, deterministic projection; IDs/field paths may be mapped, values cannot."""
    errors = validate_case(case, gps=True)
    if errors:
        raise ValueError('; '.join(errors))
    mapping = mapping or {}
    unknown = set(mapping) - {'documents', 'persons', 'tree_person_pointers', 'tree_notes_field'}
    if unknown:
        raise ValueError('Unknown mapping fields: ' + ', '.join(sorted(unknown)))
    sources = {s['id']: s for s in case['sources']}
    citations = {c['id']: c for c in case['citations']}
    mentions = {m['id']: m for m in case['mentions']}
    people = {p['id']: p for p in case['persons']}
    for key, allowed in [('documents', sources), ('persons', people), ('tree_person_pointers', people)]:
        if not isinstance(mapping.get(key, {}), dict) or set(mapping.get(key, {})) - allowed.keys():
            raise ValueError('Invalid mapping IDs for ' + key)
        if any(not isinstance(v, str) or not v.strip() for v in mapping.get(key, {}).values()):
            raise ValueError('Mapping values must be nonempty strings for ' + key)
    def person_id(subject):
        pid = mentions.get(subject, {}).get('person_id', subject)
        return mapping.get('persons', {}).get(pid, pid) if pid in people else None
    records = {}
    omissions = []
    for obs in sorted(current_observations(case), key=lambda x: x['id']):
        sid = obs['source_id']
        doc = mapping.get('documents', {}).get(sid, sid)
        if not isinstance(doc, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', doc):
            raise ValueError('Unsafe document filename; supply a documents mapping for ' + sid)
        row = {'id': obs['id'], 'person': person_id(obs.get('subject_id')),
            'mention_id': obs.get('subject_id') if obs.get('subject_id') in mentions else None,
            'role': obs.get('role'), 'field': obs.get('predicate'),
            'value': copy.deepcopy(obs.get('value', obs['statement'])),
            'evidence_class': obs.get('evidence_class', 'testimony' if sources[sid]['source_type'] == 'testimony' else 'stated'),
            'location': obs['locator'], 'note': obs['statement'], 'uncertainty': obs['uncertainty'],
            'source_id': sid, 'citation': copy.deepcopy(citations.get(obs.get('citation_id'))),
            'processing_run_id': obs.get('processing_run_id'), 'source_version_id': obs.get('source_version_id'),
            'supersedes': obs.get('supersedes')}
        for key in ('external_run', 'reading_method'):
            if obs.get(key):
                row[key] = copy.deepcopy(obs[key])
        records.setdefault(doc, []).append(row)
    notes = {person_id(pid): [] for pid in sorted(people)}
    if len(notes) != len(people):
        raise ValueError('Person ID mapping must be one-to-one; projection cannot merge identities.')
    observations = {o['id']: o for o in case['observations']}
    current = {o['id'] for o in current_observations(case)}
    for c in sorted(case['conclusions'], key=lambda x: x['id']):
        if c['status'] == 'superseded':
            continue
        pids = {person_id(observations[o].get('subject_id')) for o in c['observation_ids']}
        for rel in case['relationships']:
            if rel['conclusion_id'] == c['id']:
                pids.update([person_id(rel['from_person_id']), person_id(rel['to_person_id'])])
        pids.discard(None)
        if not pids:
            omissions.append({'conclusion_id': c['id'], 'reason': 'No resolved person association'})
        note = {'generated_by': 'genealogy-case', 'case_id': case['case_id'], 'conclusion_id': c['id'],
            'text': c['claim'], 'status': c['status'], 'rationale': c['rationale'],
            'evidence_assessment': copy.deepcopy(c.get('evidence_assessment')),
            'review_required': bool(c.get('review_required') or set(c['observation_ids']) - current),
            'observations': [copy.deepcopy(observations[o]) for o in c['observation_ids']],
            'citations': [copy.deepcopy(citations[cid]) for cid in sorted({observations[o].get('citation_id')
                           for o in c['observation_ids']} - {None})]}
        for pid in sorted(pids):
            notes[pid].append(copy.deepcopy(note))
    metadata = {'generated_by': 'genealogy-case', 'case_id': case['case_id'],
        'case_revision': case['revision'], 'case_digest': fingerprint(case),
        'visibility': 'private', 'editable': False}
    files = {'data/facts/' + doc + '.json': {**metadata, 'document_id': doc, 'facts': rows}
             for doc, rows in sorted(records.items())}
    files['data/tree-notes.json'] = {**metadata, 'people': notes}
    if tree is not None:
        pointers = mapping.get('tree_person_pointers', {})
        if set(pointers) != set(people):
            raise ValueError('Provide one tree_person_pointers JSON pointer for every case person.')
        if len(set(pointers.values())) != len(pointers):
            raise ValueError('Tree pointers must identify distinct people.')
        target = copy.deepcopy(tree)
        field = mapping.get('tree_notes_field', 'research_notes')
        if not isinstance(field, str) or not field.strip():
            raise ValueError('tree_notes_field must be a nonempty field name.')
        def strip_previous(node):
            if isinstance(node, dict):
                if isinstance(node.get(field), list):
                    node[field] = [n for n in node[field] if not (isinstance(n, dict)
                        and n.get('generated_by') == 'genealogy-case' and n.get('case_id') == case['case_id'])]
                for child in node.values():
                    strip_previous(child)
            elif isinstance(node, list):
                for child in node:
                    strip_previous(child)
        strip_previous(target)
        destinations = set()
        for pid, pointer in pointers.items():
            if not isinstance(pointer, str) or not pointer.startswith('/'):
                raise ValueError('Tree person path must be an explicit JSON pointer.')
            node = target
            for part in pointer[1:].split('/'):
                if re.search(r'~(?![01])', part):
                    raise ValueError('Invalid JSON pointer escape.')
                key = part.replace('~1', '/').replace('~0', '~')
                if isinstance(node, list):
                    if not re.fullmatch(r'0|[1-9][0-9]*', key):
                        raise ValueError('Array pointer requires a canonical nonnegative index.')
                    node = node[int(key)]
                else:
                    node = node[key]
            if not isinstance(node, dict) or not isinstance(node.get(field, []), list):
                raise ValueError('Tree notes destination must be a list on a person object.')
            if id(node) in destinations:
                raise ValueError('Tree pointers resolve to the same person object.')
            destinations.add(id(node))
            old_notes = node.get(field, [])
            node[field] = [n for n in old_notes if not (isinstance(n, dict)
                and n.get('generated_by') == 'genealogy-case' and n.get('case_id') == case['case_id'])] + notes[person_id(pid)]
        files['data/tree.json'] = target
    files['projection-report.json'] = {**metadata, 'schema': 'genealogy-private-projection/1.0',
        'mapping_digest': fingerprint(mapping), 'files': sorted(files), 'omissions': omissions,
        'limits': ['Generated private views; not a publication allowlist.',
                   'Verify native repository schemas before adopting generated envelopes.',
                   'Observation text is a source statement, not a proof-reviewed fact.',
                   'Unmapped custom case fields remain in the canonical case.']}
    return files


def write_projection(case, out, mapping=None, tree=None):
    files = projection(case, mapping, tree)
    out = Path(out)
    if out.exists():
        raise ValueError('Destination exists; use a fresh build directory and review the diff.')
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=out.name + '.', dir=out.parent))
    try:
        for rel, content in files.items():
            p = temporary / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.rename(out)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    reread = sub.add_parser('reread', help='Record a completed reading, supersede one observation, flag dependencies')
    reread.add_argument('case'); reread.add_argument('--old', required=True)
    reread.add_argument('--reading', required=True); reread.add_argument('--reason', required=True)
    reread.add_argument('--actor', required=True); reread.add_argument('--expected-revision', type=int, required=True)
    reread.add_argument('--external-run', help='Run reference from the host record, used when no queue run exists')
    project = sub.add_parser('project', help='Generate private facts and tree notes in a new directory')
    project.add_argument('case'); project.add_argument('--out', required=True)
    project.add_argument('--mapping'); project.add_argument('--tree')
    args = parser.parse_args(argv)
    try:
        if args.command == 'reread':
            reading = json.loads(Path(args.reading).read_text(encoding='utf-8'))
            if args.external_run is not None:
                given = reading.get('external_run', {})
                if not isinstance(given, dict) or given.get('ref', args.external_run) != args.external_run:
                    raise ValueError('--external-run differs from external_run in the reading.')
                reading['external_run'] = {**given, 'ref': args.external_run}
            result, changed = save_reread(args.case, old_id=args.old, reading=reading,
                reason=args.reason, actor=args.actor, expected_revision=args.expected_revision)
            print(json.dumps({'changed': changed, 'revision': result['revision'], 'next_action': result['checkpoint']['next_action']}))
        else:
            case = json.loads(Path(args.case).read_text(encoding='utf-8'))
            mapping = json.loads(Path(args.mapping).read_text(encoding='utf-8')) if args.mapping else None
            tree = json.loads(Path(args.tree).read_text(encoding='utf-8')) if args.tree else None
            files = write_projection(case, args.out, mapping, tree)
            print(json.dumps({'status': 'generated', 'path': args.out, 'files': sorted(files)}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
