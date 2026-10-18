#!/usr/bin/env python3
"""Offline interview state helper. The host agent interprets answers; this does not."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

SKILL = Path(__file__).resolve().parents[1]
COORDINATOR = SKILL.parent / 'genealogy-mode'
sys.path.insert(0, str(COORDINATOR / 'scripts'))
from case_tools import check_shape, validate_case


def uid(prefix):
    return prefix + '-' + uuid.uuid4().hex[:12]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def create_case(goal='Start my family investigation', language='en'):
    case = json.loads((COORDINATOR / 'assets/case-template.json').read_text(encoding='utf-8'))
    case.update(case_id=uid('CASE'), goal=goal)
    case['questions'][0]['text'] = goal
    case['interview'] = {'version': '1.0', 'session_id': uid('INT'), 'language': language,
                         'status': 'active', 'visibility': 'private', 'focus_person_id': None,
                         'pending_question': '', 'skipped_topics': [], 'turns': []}
    case['checkpoint']['next_action'] = 'Ask who the user wants to start with, unless already supplied.'
    return case


def apply_turn(case, turn, expected_revision):
    schema = json.loads((SKILL / 'assets/turn.schema.json').read_text(encoding='utf-8'))
    errors = check_shape(turn, schema, schema)
    if errors:
        raise ValueError('; '.join(errors))
    interview = case.get('interview')
    if not interview or interview.get('version') != '1.0':
        raise ValueError('Use an interview seed case. Merge existing research through maintenance.')
    fingerprint = digest(turn)
    prior = next((t for t in interview['turns'] if t['id'] == turn['id']), None)
    if prior:
        if prior['input_digest'] != fingerprint:
            raise ValueError('Turn ID already used with different content; append a correction with a new ID.')
        return copy.deepcopy(case), False
    if case['revision'] != expected_revision:
        raise ValueError('Revision changed; reload and reconcile before retrying.')
    if any(c['status'] in ('supported', 'rejected') for c in case['conclusions']):
        raise ValueError('Reviewed case: apply evidence changes through research-maintenance and GPS review.')
    result = copy.deepcopy(case)
    state = result['interview']
    source_id, citation_id = uid('SRC'), uid('CIT')
    locator = 'Interview ' + state['session_id'] + ', turn ' + turn['id']
    result['sources'].append({'id': source_id, 'title': 'Interview testimony: ' + turn['speaker'],
        'source_type': 'testimony', 'derived_from': [], 'recorded_at': turn['recorded_at'],
        'speaker': turn['speaker'], 'interview_id': state['session_id'],
        'independence_group': state['session_id'], 'visibility': 'private'})
    result['citations'].append({'id': citation_id, 'source_id': source_id, 'locator': locator,
        'text': f"{turn['speaker']}, interview response, {turn['recorded_at']}; {locator}.",
        'quotation': turn['answer']})
    people = {p['id']: p for p in result['persons']}
    for person in turn['people']:
        pid = person['id']
        if pid in people:
            raise ValueError('Person ID exists: ' + pid + '. Refer to it in assertions; do not recreate it.')
        row = {'id': pid, 'label': person['label'], 'visibility': 'private',
               'identity_status': 'candidate', 'life_status': 'unknown'}
        result['persons'].append(row)
        people[pid] = row
        result['mentions'].append({'id': uid('MEN'), 'source_id': source_id, 'locator': locator,
                                   'literal': person['literal'], 'person_id': pid})
    ids = {row['id'] for key in ('persons', 'mentions', 'sources', 'citations', 'observations',
           'relationships', 'conclusions', 'questions', 'changes') for row in result[key]}
    affected = [source_id, citation_id] + [p['id'] for p in turn['people']]
    for assertion in turn['assertions']:
        pid = assertion['subject_id']
        if pid not in people:
            raise ValueError('Missing subject person: ' + pid)
        oid = assertion['id']
        if oid in ids:
            raise ValueError('Duplicate assertion ID: ' + oid)
        ids.add(oid)
        if assertion.get('object_person_id') and assertion['object_person_id'] not in people:
            raise ValueError('Missing relationship person')
        if assertion.get('object_person_id') == pid:
            raise ValueError('Self relationship is not allowed')
        if assertion['predicate'] in ('birth_date', 'death_date', 'marriage_date'):
            value = assertion['value']
            if not isinstance(value, dict) or not value.get('literal') or not value.get('kind'):
                raise ValueError('Dates require literal and kind; preserve partial/uncertain dates.')
        obs = {'id': oid, 'source_id': source_id, 'citation_id': citation_id, 'locator': locator,
               'subject_id': pid, 'statement': assertion['statement'], 'predicate': assertion['predicate'],
               'value': assertion['value'], 'uncertainty': assertion['uncertainty'],
               'evidence_class': 'testimony', 'knowledge_basis': assertion['knowledge_basis']}
        if assertion.get('object_person_id'):
            obs['object_person_id'] = assertion['object_person_id']
        result['observations'].append(obs)
        conclusion = {'id': uid('CON'), 'question_id': result['active_question_id'],
                      'claim': assertion['statement'], 'status': 'provisional',
                      'observation_ids': [oid], 'depends_on': [],
                      'rationale': 'Attributed interview testimony; documentary assessment remains open.',
                      'interview_id': state['session_id']}
        result['conclusions'].append(conclusion)
        if assertion.get('object_person_id'):
            result['relationships'].append({'id': uid('REL'), 'from_person_id': pid,
                'to_person_id': assertion['object_person_id'], 'type': assertion['predicate'],
                'status': 'provisional', 'conclusion_id': conclusion['id']})
        for old_id in assertion.get('supersedes', []):
            old = next((c for c in result['conclusions'] if c['id'] == old_id), None)
            if not old or old.get('interview_id') != state['session_id'] or old['status'] != 'provisional':
                raise ValueError('Only this interview’s provisional assertions may be superseded here.')
            old['status'] = 'superseded'
            old['superseded_by'] = conclusion['id']
            for rel in result['relationships']:
                if rel['conclusion_id'] == old_id:
                    rel['status'] = 'superseded'
            affected.append(old_id)
        affected.extend([oid, conclusion['id']])
    focus = turn.get('focus_person_id', state['focus_person_id'])
    if focus is not None and focus not in people:
        raise ValueError('Focus person is missing')
    state['focus_person_id'] = focus
    if turn.get('research_question'):
        if not focus:
            raise ValueError('Choose a focus person before setting the research question')
        q = {'id': uid('Q'), 'text': turn['research_question'], 'status': 'active', 'person_ids': [focus]}
        for previous in result['questions']:
            if previous['status'] == 'active': previous['status'] = 'queued'
        result['questions'].append(q)
        result['active_question_id'] = q['id']
        result['goal'] = q['text']
    if turn['action'] == 'research' and not focus:
        raise ValueError('Research handoff needs a focus person; an unnamed relative is acceptable.')
    if turn['action'] == 'pause': state['status'] = 'paused'
    elif turn['action'] == 'research': state['status'] = 'ready_for_research'
    else: state['status'] = 'active'
    if 'pending_question' in turn: state['pending_question'] = turn['pending_question']
    state['skipped_topics'] = sorted(set(state['skipped_topics'] + turn.get('skip_topics', [])))
    state['turns'].append({'id': turn['id'], 'input_digest': fingerprint, 'input': copy.deepcopy(turn),
                           'source_id': source_id, 'citation_id': citation_id, 'saved_at': now()})
    result['revision'] += 1
    result['checkpoint']['next_action'] = turn['next_action']
    result['changes'].append({'id': uid('CHG'), 'revision': result['revision'],
        'reason': 'Interview turn ' + turn['id'], 'affected_ids': affected,
        'recorded_at': now(), 'turn_id': turn['id']})
    errors = validate_case(result, gps=True)
    if errors:
        raise ValueError('; '.join(errors))
    return result, True


def save_turn(path, turn, expected_revision):
    path = Path(path).resolve()
    lock = path.with_name(path.name + '.lock')
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    temporary = None
    try:
        os.close(fd)
        case = json.loads(path.read_text(encoding='utf-8'))
        updated, changed = apply_turn(case, turn, expected_revision)
        if changed:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix=path.name + '.', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(updated, handle, ensure_ascii=False, indent=2)
                handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
        return updated, changed
    finally:
        if temporary and temporary.exists(): temporary.unlink()
        lock.unlink()


def summary(case):
    state = case['interview']
    return {'case_id': case['case_id'], 'revision': case['revision'], 'goal': case['goal'],
            'status': state['status'], 'focus_person_id': state['focus_person_id'],
            'people': case['persons'], 'relationships': case['relationships'],
            'pending_question': state['pending_question'], 'skipped_topics': state['skipped_topics'],
            'next_action': case['checkpoint']['next_action'],
            'note': 'Interview assertions remain attributed and provisional.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    new = commands.add_parser('new'); new.add_argument('--out', required=True)
    new.add_argument('--goal', default='Start my family investigation'); new.add_argument('--language', default='en')
    record = commands.add_parser('record'); record.add_argument('case'); record.add_argument('--turn', required=True)
    record.add_argument('--expected-revision', type=int, required=True)
    status = commands.add_parser('status'); status.add_argument('case')
    args = parser.parse_args(argv)
    try:
        if args.command == 'new':
            case = create_case(args.goal, args.language)
            target = Path(args.out); target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('x', encoding='utf-8') as handle:
                json.dump(case, handle, ensure_ascii=False, indent=2); handle.write('\n')
            print(json.dumps(summary(case), ensure_ascii=False, indent=2))
        elif args.command == 'record':
            turn = json.loads(Path(args.turn).read_text(encoding='utf-8'))
            case, changed = save_turn(args.case, turn, args.expected_revision)
            print(json.dumps({'changed': changed, **summary(case)}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(summary(json.loads(Path(args.case).read_text(encoding='utf-8'))), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
