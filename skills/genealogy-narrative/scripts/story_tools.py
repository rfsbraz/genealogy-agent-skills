#!/usr/bin/env python3
"""Read-only story briefs, provenance checks and Markdown rendering; no model calls."""
import argparse
import copy
import json
from pathlib import Path
import sys

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parent / 'genealogy-mode/scripts'))
from case_tools import check_shape, validate_case
from gps_review import evidence_digest


def make_brief(case, person_id):
    person = next((p for p in case['persons'] if p['id'] == person_id), None)
    if person is None: raise ValueError('Person ID not found; resolve the intended identity first.')
    subjects = {person_id} | {m['id'] for m in case['mentions'] if m.get('person_id') == person_id}
    observations = [o for o in case['observations'] if o.get('subject_id') in subjects or o.get('object_person_id') == person_id]
    relationships = [r for r in case['relationships'] if person_id in (r['from_person_id'], r['to_person_id'])]
    events = [e for e in case['events'] if subjects.intersection(e.get('participant_ids', []))]
    obs_ids = {o['id'] for o in observations} | {o for e in events for o in e['observation_ids']}
    conclusion_ids = {r['conclusion_id'] for r in relationships}
    conclusions = [c for c in case['conclusions'] if c['id'] in conclusion_ids or obs_ids.intersection(c['observation_ids'])]
    # Include competing conclusions/hypotheses for relevant questions rather than cherry-picking a preferred answer.
    question_ids = {c['question_id'] for c in conclusions}
    conclusions = [c for c in case['conclusions'] if c['question_id'] in question_ids or c in conclusions]
    hypotheses = [h for h in case['hypotheses'] if h['question_id'] in question_ids]
    for c in conclusions: obs_ids.update(c['observation_ids'])
    for h in hypotheses: obs_ids.update(h.get('support_ids', []) + h.get('counterevidence_ids', []))
    observations = [o for o in case['observations'] if o['id'] in obs_ids]
    citation_ids = {o.get('citation_id') for o in observations}
    source_ids = {o['source_id'] for o in observations}
    return {'case_id': case['case_id'], 'person': copy.deepcopy(person),
        'evidence_digest': evidence_digest(case), 'visibility': 'private',
        'observations': observations, 'conclusions': conclusions, 'relationships': relationships,
        'events': events, 'hypotheses': hypotheses,
        'citations': [c for c in case['citations'] if c['id'] in citation_ids],
        'sources': [s for s in case['sources'] if s['id'] in source_ids],
        'questions': [q for q in case['questions'] if q['id'] in question_ids],
        'case_validation_issues': validate_case(case, gps=True),
        'instruction': 'Inventory only. Check actual source support, identity, conflicts and privacy. Do not convert prose into evidence.'}


def validate_story(case, story):
    schema = json.loads((SKILL / 'assets/story.schema.json').read_text(encoding='utf-8'))
    errors = check_shape(story, schema, schema)
    if errors: return errors
    if story['case_id'] != case['case_id']: errors.append('Wrong case ID')
    if story['evidence_digest'] != evidence_digest(case): errors.append('Evidence changed; refresh and re-review this story')
    if story['person_id'] not in {p['id'] for p in case['persons']}: errors.append('Missing person ID')
    if story['mode'] == 'novelized' and not story['fiction_notice'].strip(): errors.append('Novelized stories need a visible fiction notice')
    observations = {o['id']: o for o in case['observations']}
    conclusions = {c['id']: c for c in case['conclusions']}
    citations = {c['id']: c for c in case['citations']}
    sources = {s['id']: s for s in case['sources']}
    context = {s['id']: s for s in story['context_sources']}
    if len(context) != len(story['context_sources']): errors.append('Duplicate context source ID')
    case_errors = validate_case(case, gps=True)
    seen = set()
    for block in story['blocks']:
        bid, kind = block['id'], block['kind']
        permitted_basis = {'documented': {'record_statement', 'reviewed_conclusion'},
            'recollection': {'attributed_memory'}, 'inference': {'reasoned_inference'},
            'context': {'historical_context'}, 'imagined': {'fiction'}}
        if block['basis'] not in permitted_basis[kind]:
            errors.append(bid + ': basis does not match passage kind')
        if bid in seen: errors.append('Duplicate block ID: ' + bid)
        seen.add(bid)
        oids = set(block['observation_ids'])
        cids = set(block['conclusion_ids'])
        ctx = set(block['context_ids'])
        if oids - observations.keys(): errors.append(bid + ': unknown observation')
        if cids - conclusions.keys(): errors.append(bid + ': unknown conclusion')
        if ctx - context.keys(): errors.append(bid + ': unknown context source')
        linked = set(oids)
        for cid in cids & conclusions.keys(): linked.update(conclusions[cid]['observation_ids'])
        if kind == 'imagined':
            if story['mode'] != 'novelized': errors.append(bid + ': imagined passages require novelized mode')
            if oids or cids or ctx: errors.append(bid + ': imagined prose cannot claim evidence citations')
        elif kind == 'context':
            if not ctx: errors.append(bid + ': historical context needs an inspected contextual source')
        elif kind in ('documented', 'recollection'):
            if not linked: errors.append(bid + ': evidence references required')
        elif kind == 'inference':
            if not (linked or ctx): errors.append(bid + ': inference needs an evidential basis')
        if kind == 'documented':
            if block['basis'] not in ('record_statement', 'reviewed_conclusion'):
                errors.append(bid + ': documented basis must distinguish record statement from conclusion')
            if block['basis'] == 'reviewed_conclusion':
                if not cids: errors.append(bid + ': reviewed conclusion reference required')
                if case_errors: errors.append(bid + ': current case review checks must pass')
                if any(conclusions[c]['status'] != 'supported' for c in cids & conclusions.keys()):
                    errors.append(bid + ': conclusion is not supported')
        for oid in linked & observations.keys():
            observation = observations[oid]
            if any(o.get('supersedes') == oid for o in observations.values()):
                errors.append(bid + ': cited reading has been superseded; reassess the passage')
            cit = citations.get(observation.get('citation_id'))
            if not cit or not cit.get('text') or not cit.get('locator'):
                errors.append(bid + ': full citation and locator needed for ' + oid)
            source = sources.get(observation['source_id'], {})
            if kind == 'documented' and block['basis'] == 'record_statement' and source.get('source_type') == 'testimony':
                errors.append(bid + ': testimony must be attributed as recollection or assessed as inference')
            if source.get('generated_narrative'):
                errors.append(bid + ': a generated story is not independent historical evidence')
    return errors


def render_story(case, story):
    errors = validate_story(case, story)
    if errors: raise ValueError('; '.join(errors))
    labels = {'documented': 'Documented', 'recollection': 'Recollection', 'inference': 'Inference',
              'context': 'Historical context', 'imagined': 'Imagined scene'}
    citations = {c['id']: c for c in case['citations']}
    observations = {o['id']: o for o in case['observations']}
    conclusions = {c['id']: c for c in case['conclusions']}
    context = {c['id']: c for c in story['context_sources']}
    lines = ['# ' + story['title'], '', story['intro_note'], '']
    if story['mode'] == 'novelized': lines += ['**' + story['fiction_notice'] + '**', '']
    for number, block in enumerate(story['blocks'], 1):
        lines += [block['text'].rstrip() + f' [^{number}]', '']
    lines += ['## Behind the story', '']
    for number, block in enumerate(story['blocks'], 1):
        refs, oids = [], set(block['observation_ids'])
        for cid in block['conclusion_ids']: oids.update(conclusions[cid]['observation_ids'])
        for oid in sorted(oids):
            cit = citations[observations[oid]['citation_id']]
            if cit['text'] not in refs: refs.append(cit['text'])
        refs.extend(context[c]['citation'] for c in block['context_ids'])
        note = ' '.join([labels[block['kind']] + '.', block['note']] + refs)
        lines += [f'[^{number}]: ' + note.replace('\n', ' '), '']
    if story['unresolved']:
        lines += ['### Questions still open', ''] + ['- ' + q for q in story['unresolved']] + ['']
    lines += ['Private working story. Source snapshot: `' + story['evidence_digest'] + '`.']
    return '\n'.join(lines) + '\n'


def write_new(path, content):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle: handle.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    brief = commands.add_parser('brief'); brief.add_argument('case'); brief.add_argument('--person', required=True); brief.add_argument('--out', required=True)
    for command in ('check', 'render'):
        p = commands.add_parser(command); p.add_argument('case'); p.add_argument('story')
        if command == 'render': p.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        case = json.loads(Path(args.case).read_text(encoding='utf-8'))
        if args.command == 'brief':
            write_new(args.out, json.dumps(make_brief(case, args.person), ensure_ascii=False, indent=2) + '\n')
            print('Private brief created. The case was not changed.')
        else:
            story = json.loads(Path(args.story).read_text(encoding='utf-8'))
            errors = validate_story(case, story)
            if args.command == 'check':
                print(json.dumps({'valid': not errors, 'errors': errors,
                    'scope': 'Structure and references only; editorial and privacy review still required.'}, indent=2))
                return 1 if errors else 0
            if errors: raise ValueError('; '.join(errors))
            write_new(args.out, render_story(case, story))
            print('Private story rendered with evidence notes. The case was not changed.')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
