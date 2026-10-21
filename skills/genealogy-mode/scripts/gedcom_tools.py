#!/usr/bin/env python3
"""GEDCOM helpers: a pre-import check, import into a provisional case, and export of reviewed conclusions. Standard library only, no network.

An imported tree is a claim to test, not evidence. Import keeps the GEDCOM file as the source actually
consulted, turns each fact into a cited observation with a provisional conclusion, and never marks
anything supported. The tree's own citations are kept as leads on the observations. Export goes the other way: only
supported and source_supported claims, each with its sources, plus a report of what GEDCOM cannot carry.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
from case_tools import ASSETS, validate_case

LINE = re.compile(r'^\s*(\d+)\s+(?:(@[^@\s]+@)\s+)?([A-Za-z0-9_]+)(?: (.*))?$')
MONTHS = {m: i for i, m in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split(), 1)}
PERSON_EVENTS = {'BIRT': 'birth', 'CHR': 'baptism', 'BAPM': 'baptism', 'DEAT': 'death', 'BURI': 'burial'}
FAMILY_EVENTS = {'MARR': 'marriage', 'DIV': 'divorce'}
APPROX_SLACK = 5   # years either side of ABT, CAL and EST dates
MAX_LIFESPAN = 120
MIN_PARENT_AGE = 12
MAX_MOTHER_AGE = 55
DUPLICATE_YEARS = 2


# ---------------------------------------------------------------- parsing

def _nodes(path):
    raw = Path(path).read_bytes()
    text = raw.decode('utf-8-sig', errors='replace')
    roots, stack = [], []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = LINE.match(line)
        if not match:
            raise ValueError(f'{Path(path).name} line {number}: not a GEDCOM line: {line[:60]!r}')
        level = int(match.group(1))
        node = {'level': level, 'xref': match.group(2), 'tag': match.group(3).upper(),
                'value': match.group(4) or '', 'children': [], 'line': number}
        while stack and stack[-1]['level'] >= level:
            stack.pop()
        if level == 0:
            roots.append(node)
        elif not stack or stack[-1]['level'] != level - 1:
            raise ValueError(f'{Path(path).name} line {number}: level {level} does not follow its parent')
        elif node['tag'] == 'CONT':
            stack[-1]['value'] += '\n' + node['value']
            continue
        elif node['tag'] == 'CONC':
            stack[-1]['value'] += node['value']
            continue
        else:
            stack[-1]['children'].append(node)
        stack.append(node)
    return roots, raw


def _first(node, tag):
    return next((c for c in node['children'] if c['tag'] == tag), None)


def _value(node, tag):
    child = _first(node, tag)
    return child['value'] if child else None


def _citations(node):
    return [{'source': c['value'], 'page': _value(c, 'PAGE')} for c in node['children'] if c['tag'] == 'SOUR']


def _event(node, notes):
    return {'tag': node['tag'], 'date': _value(node, 'DATE'), 'place': _value(node, 'PLAC'),
            'sources': _citations(node), 'line': node['line'],
            'notes': [_note(c, notes) for c in node['children'] if c['tag'] == 'NOTE']}


def _note(node, notes):
    return notes.get(node['value'], node['value']) if node['value'].startswith('@') else node['value']


def clean_name(value):
    return ' '.join(value.replace('/', ' ').split())


def parse_gedcom(path):
    """Read a GEDCOM 5.5.1 or 7.0 file into individuals, families and sources keyed by xref."""
    roots, raw = _nodes(path)
    notes = {r['xref']: r['value'] for r in roots if r['tag'] == 'NOTE' and r['xref']}
    tree = {'version': None, 'individuals': {}, 'families': {}, 'sources': {}, 'skipped': {},
            'sha256': hashlib.sha256(raw).hexdigest(), 'file': Path(path).name}
    for root in roots:
        tag = root['tag']
        if tag == 'HEAD':
            gedc = _first(root, 'GEDC')
            tree['version'] = _value(gedc, 'VERS') if gedc else None
        elif tag == 'INDI':
            name = _first(root, 'NAME')
            tree['individuals'][root['xref']] = {
                'xref': root['xref'], 'name': clean_name(name['value']) if name else '',
                'name_literal': name['value'] if name else '', 'sex': _value(root, 'SEX'),
                'events': [_event(c, notes) for c in root['children'] if c['tag'] in PERSON_EVENTS],
                'famc': [c['value'] for c in root['children'] if c['tag'] == 'FAMC'],
                'fams': [c['value'] for c in root['children'] if c['tag'] == 'FAMS'],
                'notes': [_note(c, notes) for c in root['children'] if c['tag'] == 'NOTE'],
                'sources': _citations(root), 'line': root['line']}
        elif tag == 'FAM':
            tree['families'][root['xref']] = {
                'xref': root['xref'], 'husband': _value(root, 'HUSB'), 'wife': _value(root, 'WIFE'),
                'children': [c['value'] for c in root['children'] if c['tag'] == 'CHIL'],
                'events': [_event(c, notes) for c in root['children'] if c['tag'] in FAMILY_EVENTS],
                'sources': _citations(root), 'line': root['line']}
        elif tag == 'SOUR':
            tree['sources'][root['xref']] = {'xref': root['xref'], 'title': _value(root, 'TITL') or '',
                                             'author': _value(root, 'AUTH')}
        elif tag not in ('TRLR', 'NOTE'):
            tree['skipped'][tag] = tree['skipped'].get(tag, 0) + 1
    return tree


# ---------------------------------------------------------------- dates

def _point(text):
    """'12 MAR 1890', 'MAR 1890' or '1890' -> (iso, kind), or ('invalid', reason), or None."""
    parts = text.split()
    if parts and parts[-1].upper() == 'B.C.':
        return None
    try:
        if len(parts) == 3 and parts[1].upper() in MONTHS and parts[0].isdigit() and parts[2].isdigit():
            day = date(int(parts[2]), MONTHS[parts[1].upper()], int(parts[0]))
            return day.isoformat(), 'exact'
        if len(parts) == 2 and parts[0].upper() in MONTHS and parts[1].isdigit():
            return f'{int(parts[1]):04d}-{MONTHS[parts[0].upper()]:02d}', 'month'
        if len(parts) == 1 and parts[0].isdigit():
            return f'{int(parts[0]):04d}', 'year'
    except ValueError:
        return 'invalid', 'no such day'
    return None


def parse_date(literal):
    """Keep the literal and add a kind plus earliest/latest bounds (ISO prefixes), never a guess."""
    text = ' '.join((literal or '').split())
    value = {'literal': literal, 'kind': 'unparsed', 'calendar': 'gregorian', 'earliest': None, 'latest': None}
    calendar = re.match(r'^@#D([A-Z ]+)@\s*(.*)$', text)
    if calendar:
        value['calendar'] = calendar.group(1).strip().lower()
        text = calendar.group(2)
    upper = text.upper()
    if not text:
        value['kind'] = 'empty'
        return value
    if text.startswith('(') or upper.startswith('INT '):
        value['kind'] = 'text'
        return value
    def bounds(kind, first, second=None):
        a = _point(first)
        b = _point(second) if second is not None else a
        if a and a[0] == 'invalid' or b and b[0] == 'invalid':
            value['kind'] = 'invalid'
        elif a and b:
            value.update(kind=kind, earliest=a[0], latest=b[0])
        return value
    for prefix in ('ABT ', 'CAL ', 'EST '):
        if upper.startswith(prefix):
            return bounds('approximate', text[4:])
    if upper.startswith('BEF '):
        bounds('before', text[4:])
        if value['kind'] == 'before':
            value['earliest'] = None
        return value
    if upper.startswith('AFT '):
        bounds('after', text[4:])
        if value['kind'] == 'after':
            value['latest'] = None
        return value
    between = re.match(r'^(?:BET|FROM) (.+?) (?:AND|TO) (.+)$', text, re.I)
    if between:
        return bounds('range', between.group(1), between.group(2))
    if upper.startswith('FROM ') or upper.startswith('TO '):
        return bounds('range', text.split(' ', 1)[1])
    point = _point(text)
    if point and point[0] == 'invalid':
        value['kind'] = 'invalid'
    elif point:
        value.update(kind=point[1], earliest=point[0], latest=point[0])
    return value


def year_bounds(value):
    """(low, high) years for checks; None on an open side. Approximate dates are widened."""
    if not value or value['kind'] in ('invalid', 'text', 'unparsed', 'empty'):
        return None
    low = int(value['earliest'][:4]) if value['earliest'] else None
    high = int(value['latest'][:4]) if value['latest'] else None
    if value['kind'] == 'approximate':
        low, high = low - APPROX_SLACK, high + APPROX_SLACK
    return low, high


# ---------------------------------------------------------------- pre-import check

def _event_bounds(person, kinds):
    for event in person.get('events', []):
        if PERSON_EVENTS.get(event['tag']) in kinds and event['date']:
            bounds = year_bounds(parse_date(event['date']))
            if bounds:
                return bounds
    return None


def _fold(name):
    plain = unicodedata.normalize('NFKD', name)
    return ' '.join(''.join(c for c in plain if not unicodedata.combining(c)).casefold().split())


def check_tree(tree, today=None):
    """Duplicates, impossible dates and impossible parent/child ages. Errors are impossible; warnings are doubtful."""
    today = today or date.today()
    people, families = tree['individuals'], tree['families']
    issues = []

    def add(kind, severity, records, detail):
        issues.append({'kind': kind, 'severity': severity, 'records': list(records), 'detail': detail})

    def label(xref):
        person = people.get(xref)
        return f"{person['name'] or 'unnamed'} ({xref})" if person else xref

    known = set(people) | set(families) | set(tree['sources'])
    for xref, person in people.items():
        for pointer in person['famc'] + person['fams'] + [s['source'] for s in person['sources']]:
            if pointer.startswith('@') and pointer not in known:
                add('missing_record', 'error', [xref], f'{label(xref)} points to {pointer}, which is not in the file.')
        for event in person['events']:
            parsed = parse_date(event['date']) if event['date'] else None
            if parsed and parsed['kind'] == 'invalid':
                add('invalid_date', 'error', [xref], f"{label(xref)}: {event['tag']} date {event['date']!r} is not a real date.")
            elif parsed and parsed['kind'] == 'unparsed':
                add('unparsed_date', 'warning', [xref], f"{label(xref)}: {event['tag']} date {event['date']!r} is not in GEDCOM date form.")
            bounds = year_bounds(parsed)
            if bounds and bounds[0] is not None and bounds[0] > today.year:
                add('future_date', 'error', [xref], f"{label(xref)}: {event['tag']} date {event['date']!r} is in the future.")
        birth = _event_bounds(person, ('birth', 'baptism'))
        death = _event_bounds(person, ('death', 'burial'))
        if birth and death:
            if death[1] is not None and birth[0] is not None and death[1] < birth[0]:
                add('death_before_birth', 'error', [xref], f'{label(xref)} dies or is buried before being born.')
            elif death[0] is not None and birth[1] is not None and death[0] - birth[1] > MAX_LIFESPAN:
                add('implausible_lifespan', 'error', [xref], f'{label(xref)} would have lived more than {MAX_LIFESPAN} years.')

    for fxref, family in families.items():
        members = [family['husband'], family['wife']] + family['children']
        for pointer in members:
            if pointer and pointer not in people:
                add('missing_record', 'error', [fxref], f'Family {fxref} points to {pointer}, which is not in the file.')
        for event in family['events']:
            parsed = parse_date(event['date']) if event['date'] else None
            if parsed and parsed['kind'] == 'invalid':
                add('invalid_date', 'error', [fxref], f"Family {fxref}: {event['tag']} date {event['date']!r} is not a real date.")
            married = year_bounds(parsed)
            if not married or event['tag'] != 'MARR':
                continue
            for spouse in (family['husband'], family['wife']):
                if spouse not in people:
                    continue
                birth = _event_bounds(people[spouse], ('birth', 'baptism'))
                death = _event_bounds(people[spouse], ('death', 'burial'))
                if birth and married[1] is not None and birth[0] is not None and married[1] < birth[0]:
                    add('married_before_birth', 'error', [spouse, fxref], f'{label(spouse)} marries before being born.')
                elif birth and married[1] is not None and birth[0] is not None and married[1] - birth[0] < MIN_PARENT_AGE:
                    add('married_very_young', 'warning', [spouse, fxref], f'{label(spouse)} would marry under age {MIN_PARENT_AGE}.')
                if death and married[0] is not None and death[1] is not None and married[0] > death[1]:
                    add('married_after_death', 'error', [spouse, fxref], f'{label(spouse)} marries after dying.')
        for child in family['children']:
            if child not in people:
                continue
            cb = _event_bounds(people[child], ('birth', 'baptism'))
            for parent, role in ((family['husband'], 'father'), (family['wife'], 'mother')):
                if parent not in people or not cb:
                    continue
                pb = _event_bounds(people[parent], ('birth', 'baptism'))
                pd = _event_bounds(people[parent], ('death', 'burial'))
                if pb and pb[0] is not None and cb[1] is not None:
                    if pb[0] >= cb[1]:
                        add('parent_younger_than_child', 'error', [parent, child],
                            f'{label(parent)} is born no earlier than their child {label(child)}.')
                    elif cb[1] - pb[0] < MIN_PARENT_AGE:
                        add('parent_too_young', 'warning', [parent, child],
                            f'{label(parent)} would be under {MIN_PARENT_AGE} at the birth of {label(child)}.')
                if role == 'mother' and pb and pb[1] is not None and cb[0] is not None and cb[0] - pb[1] > MAX_MOTHER_AGE:
                    add('mother_too_old', 'warning', [parent, child],
                        f'{label(parent)} would be over {MAX_MOTHER_AGE} at the birth of {label(child)}.')
                grace = 1 if role == 'father' else 0
                if pd and pd[1] is not None and cb[0] is not None and cb[0] > pd[1] + grace:
                    add('born_after_parent_death', 'error', [parent, child],
                        f'{label(child)} is born after the death of their {role} {label(parent)}.')

    parents = {}
    for family in families.values():
        for child in family['children']:
            parents.setdefault(child, set()).update(p for p in (family['husband'], family['wife']) if p)
    for start in people:
        seen, frontier = set(), list(parents.get(start, ()))
        while frontier:
            current = frontier.pop()
            if current == start:
                add('ancestry_cycle', 'error', [start], f'{label(start)} is listed as their own ancestor.')
                break
            if current not in seen:
                seen.add(current)
                frontier.extend(parents.get(current, ()))

    by_name = {}
    for xref, person in people.items():
        if person['name']:
            by_name.setdefault(_fold(person['name']), []).append(xref)
    for group in by_name.values():
        for i, a in enumerate(sorted(group)):
            for b in sorted(group)[i + 1:]:
                ba = _event_bounds(people[a], ('birth', 'baptism'))
                bb = _event_bounds(people[b], ('birth', 'baptism'))
                close = (ba and bb and None not in ba + bb
                         and ba[0] - DUPLICATE_YEARS <= bb[1] and bb[0] - DUPLICATE_YEARS <= ba[1])
                same_parents = bool(set(people[a]['famc']) & set(people[b]['famc']))
                if close or (not ba and not bb and same_parents):
                    add('possible_duplicate', 'warning', [a, b],
                        f'{label(a)} and {label(b)} have the same name and close or missing birth dates.')

    issues.sort(key=lambda i: (i['severity'] != 'error', i['kind'], i['records']))
    return {'file': tree['file'], 'gedcom_version': tree['version'], 'individuals': len(people),
            'families': len(families), 'skipped_records': tree['skipped'],
            'errors': sum(i['severity'] == 'error' for i in issues),
            'warnings': sum(i['severity'] == 'warning' for i in issues), 'issues': issues,
            'scope': 'Internal consistency of the tree only; it does not check any fact against records.'}


# ---------------------------------------------------------------- import

PREDICATES = {'birth': 'birth_date', 'baptism': 'baptism_date', 'death': 'death_date',
              'burial': 'burial_date', 'marriage': 'marriage_date', 'divorce': 'divorce_date'}
UNCERTAINTY = "Copied from an imported tree; the tree's own evidence has not been checked."
RATIONALE = 'Imported tree claim. Test it against records before relying on it.'


def _key(xref):
    return re.sub(r'[^A-Za-z0-9]+', '-', xref.strip('@')).strip('-') or 'X'


def import_tree(tree, question=None, case_id=None, prefix='GED'):
    case = json.loads((ASSETS / 'case-template.json').read_text(encoding='utf-8'))
    report = check_tree(tree)
    goal = question or f"Review the imported tree {tree['file']} and choose its first claim to test."
    case.update(case_id=case_id or f"C-{prefix}-{tree['sha256'][:10]}", goal=goal)
    case['questions'][0]['text'] = goal
    qid = case['active_question_id']
    source_id = f"S-{prefix}-{tree['sha256'][:10]}"
    case['sources'].append({
        'id': source_id, 'title': f"GEDCOM file {tree['file']}", 'source_type': 'authored',
        'reference': tree['file'], 'derived_from': [], 'sha256': tree['sha256'],
        'gedcom_version': tree['version'], 'visibility': 'private',
        'note': 'An imported tree is a claim to test, not evidence of the events it lists.'})
    people = tree['individuals']
    pid = {x: f'P-{prefix}-{_key(x)}' for x in people}
    places = {}

    def place_id(literal):
        if literal and literal not in places:
            places[literal] = f'PL-{prefix}-{len(places) + 1}'
            case['places'].append({'id': places[literal], 'literal': literal, 'candidates': []})
        return places.get(literal)

    def citation(xref, what):
        cid = f'CIT-{prefix}-{_key(xref)}'
        if not any(c['id'] == cid for c in case['citations']):
            case['citations'].append({'id': cid, 'source_id': source_id, 'locator': f'GEDCOM record {xref}',
                                      'text': f"{tree['file']}, GEDCOM record {xref} ({what})."})
        return cid

    def leads(sources):
        return [{'title': tree['sources'].get(s['source'], {}).get('title') or s['source'], 'page': s['page']}
                for s in sources]

    def observe(oid, xref, what, subject, predicate, value, statement, sources=(), **extra):
        row = {'id': oid, 'source_id': source_id, 'citation_id': citation(xref, what),
               'locator': f'GEDCOM record {xref}', 'subject_id': subject, 'statement': statement,
               'predicate': predicate, 'value': value, 'uncertainty': UNCERTAINTY, 'evidence_class': 'imported_tree'}
        if sources:
            row['tree_citations'] = leads(sources)
        row.update(extra)
        case['observations'].append(row)
        return oid

    def conclude(cid, oid, claim):
        case['conclusions'].append({'id': cid, 'question_id': qid, 'claim': claim, 'status': 'provisional',
                                    'observation_ids': [oid], 'rationale': RATIONALE, 'depends_on': []})
        return cid

    def event_rows(owner_xref, owner_label, event, n, subject, participants, object_person=None):
        kind = PERSON_EVENTS.get(event['tag']) or FAMILY_EVENTS[event['tag']]
        key = f"{_key(owner_xref)}-{event['tag']}-{n}"
        value = parse_date(event['date']) if event['date'] else None
        where = place_id(event['place'])
        said = ' '.join(x for x in (f"on or about {event['date']}" if event['date'] else '',
                                    f"at {event['place']}" if event['place'] else '') if x) or 'with no date or place'
        extra = {'place_id': where} if where else {}
        if object_person:
            extra['object_person_id'] = object_person
        oid = observe(f'OBS-{prefix}-{key}', owner_xref, owner_label, subject, PREDICATES[kind], value,
                      f"The imported tree gives the {kind} of {owner_label} {said}.", event['sources'], **extra)
        conclude(f'CON-{prefix}-{key}', oid, f"{owner_label}: {kind} {said} (imported tree).")
        case['events'].append({'id': f'EV-{prefix}-{key}', 'type': kind, 'observation_ids': [oid],
                               'participant_ids': participants, **({'place_id': where} if where else {}),
                               **({'date': value} if value else {})})
        for note in event['notes']:
            observe(f'OBS-{prefix}-{key}-NOTE', owner_xref, owner_label, subject, 'note', note,
                    f"The imported tree has a note on the {kind} of {owner_label}.")

    for xref, person in people.items():
        name = person['name'] or f'Unnamed person {xref}'
        row = {'id': pid[xref], 'label': name, 'visibility': 'private', 'identity_status': 'candidate',
               'life_status': 'unknown', 'gedcom_xref': xref}
        case['persons'].append(row)
        case['mentions'].append({'id': f'MEN-{prefix}-{_key(xref)}', 'source_id': source_id,
                                 'locator': f'GEDCOM record {xref}', 'literal': person['name_literal'] or name,
                                 'person_id': pid[xref]})
        if person['name_literal']:
            observe(f'OBS-{prefix}-{_key(xref)}-NAME', xref, name, pid[xref], 'reported_name', person['name'],
                    f'The imported tree names this person {name}.', person['sources'])
        if person['sex']:
            observe(f'OBS-{prefix}-{_key(xref)}-SEX', xref, name, pid[xref], 'sex', person['sex'],
                    f"The imported tree records {name}'s sex as {person['sex']}.")
        for n, event in enumerate(person['events'], 1):
            event_rows(xref, name, event, n, pid[xref], [pid[xref]])
        for n, note in enumerate(person['notes'], 1):
            observe(f'OBS-{prefix}-{_key(xref)}-NOTE-{n}', xref, name, pid[xref], 'note', note,
                    f'The imported tree has a note on {name}.')

    for fxref, family in tree['families'].items():
        spouses = [s for s in (family['husband'], family['wife']) if s in people]
        flabel = 'family ' + fxref
        if len(spouses) == 2:
            a, b = (pid[s] for s in spouses)
            names = ' and '.join(people[s]['name'] or s for s in spouses)
            oid = observe(f'OBS-{prefix}-{_key(fxref)}-SPOUSE', fxref, flabel, a, 'spouse', None,
                          f'The imported tree lists {names} as a couple in {flabel}.', family['sources'],
                          object_person_id=b)
            con = conclude(f'CON-{prefix}-{_key(fxref)}-SPOUSE', oid, f'{names} were a couple (imported tree).')
            case['relationships'].append({'id': f'REL-{prefix}-{_key(fxref)}-SPOUSE', 'from_person_id': a,
                                          'to_person_id': b, 'type': 'spouse', 'status': 'provisional',
                                          'conclusion_id': con})
        for n, event in enumerate(family['events'], 1):
            if spouses:
                event_rows(fxref, flabel, event, n, pid[spouses[0]], [pid[s] for s in spouses],
                           pid[spouses[1]] if len(spouses) == 2 else None)
        for child in family['children']:
            if child not in people:
                continue
            for parent in spouses:
                key = f'{_key(fxref)}-{_key(parent)}-{_key(child)}'
                pname, cname = people[parent]['name'] or parent, people[child]['name'] or child
                oid = observe(f'OBS-{prefix}-{key}', fxref, flabel, pid[parent], 'parent', None,
                              f'The imported tree lists {pname} as a parent of {cname} in {flabel}.',
                              family['sources'], object_person_id=pid[child])
                con = conclude(f'CON-{prefix}-{key}', oid, f'{pname} was a parent of {cname} (imported tree).')
                case['relationships'].append({'id': f'REL-{prefix}-{key}', 'from_person_id': pid[parent],
                                              'to_person_id': pid[child], 'type': 'parent',
                                              'status': 'provisional', 'conclusion_id': con})

    for n, issue in enumerate(report['issues'], 1):
        case['tasks'].append({'id': f'TASK-{prefix}-CHECK-{n}', 'question_id': qid, 'status': 'planned',
                              'action': f"Resolve before relying on the tree ({issue['severity']}): {issue['detail']}",
                              'import_issue': issue['kind'],
                              'person_ids': [pid[r] for r in issue['records'] if r in pid]})
    case['import_check'] = report
    case['revision'] = 1
    case['changes'].append({'id': f'CHG-{prefix}-IMPORT', 'revision': 1,
                            'reason': f"Imported GEDCOM file {tree['file']} as provisional tree claims.",
                            'affected_ids': [source_id] + [pid[x] for x in people]})
    case['checkpoint']['next_action'] = ('Resolve the import check tasks, then choose one tree claim to test against records.'
                                         if report['issues'] else 'Choose one tree claim to test against records.')
    errors = validate_case(case, gps=True)
    if errors:
        raise ValueError('import produced an invalid case: ' + '; '.join(errors[:5]))
    return case


# ---------------------------------------------------------------- export

EXPORT_TAGS = {
    'birth': 'BIRT', 'birth_date': 'BIRT', 'baptism': 'CHR', 'baptism_date': 'CHR', 'christening': 'CHR',
    'death': 'DEAT', 'death_date': 'DEAT', 'burial': 'BURI', 'burial_date': 'BURI',
    'residence': 'RESI', 'occupation': 'OCCU',
}
FAMILY_TAGS = {'marriage': 'MARR', 'marriage_date': 'MARR', 'divorce': 'DIV', 'divorce_date': 'DIV'}
PARENT_TYPES = ('parent', 'biological_parent')
REVIEWED = ('supported', 'source_supported')
ALWAYS_LOST = [
    'observation statements, literal wording and uncertainty notes',
    'GPS reviews and evidence assessments (only their status is noted on each fact)',
    'hypotheses, searches, tasks and correspondence',
    'rejected, superseded and unresolved conclusions, and the change history',
    'mentions that are not linked to a person, and identity decisions',
]
MONTH_NAMES = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split()


def gedcom_lines(level, tag, value='', xref=None):
    """One GEDCOM line, with CONT for line breaks and CONC so no line passes 255 characters."""
    head = f"{level} {xref + ' ' if xref else ''}{tag}"
    parts = str(value or '').split('\n')
    lines = []
    for i, part in enumerate(parts):
        prefix = head if i == 0 else f'{level + 1} CONT'
        room = 250 - len(prefix)
        chunk, part = part[:room], part[room:]
        lines.append(f'{prefix} {chunk}'.rstrip() if chunk or i else prefix)
        while part:
            room = 250 - len(f'{level + 1} CONC ')
            chunk, part = part[:room], part[room:]
            lines.append(f'{level + 1} CONC {chunk}')
    return lines


def _iso_to_gedcom(iso):
    bits = iso.split('-')
    if len(bits) == 3:
        return f'{int(bits[2])} {MONTH_NAMES[int(bits[1]) - 1]} {int(bits[0])}'
    if len(bits) == 2:
        return f'{MONTH_NAMES[int(bits[1]) - 1]} {int(bits[0])}'
    return str(int(bits[0]))


def gedcom_date(value):
    """A case date object (or literal) as a GEDCOM date; a free-text phrase when it has no GEDCOM form."""
    if not value:
        return None
    literal = value.get('literal') if isinstance(value, dict) else str(value)
    parsed = parse_date(literal) if literal else None
    if parsed and parsed['kind'] not in ('invalid', 'text', 'unparsed', 'empty'):
        return ' '.join(literal.upper().split())
    if isinstance(value, dict):
        exact = value.get('date') or (value.get('earliest') if value.get('earliest') == value.get('latest') else None)
        try:
            if exact:
                return _iso_to_gedcom(exact)
            if value.get('earliest') and value.get('latest'):
                return f"BET {_iso_to_gedcom(value['earliest'])} AND {_iso_to_gedcom(value['latest'])}"
        except (ValueError, IndexError):
            pass
    return f'({literal})' if literal else None


def export_case(case, include=REVIEWED):
    """GEDCOM 5.5.1 text and a loss report for the claims whose status is in `include`."""
    errors = validate_case(case, gps=case.get('schema_version') in ('1.1', '1.2'))
    if errors:
        raise ValueError('case does not validate; fix it before exporting: ' + '; '.join(errors[:5]))
    persons = {p['id']: p for p in case['persons']}
    mentions = {m['id']: m for m in case['mentions']}
    observations = {o['id']: o for o in case['observations']}
    sources = {s['id']: s for s in case['sources']}
    citations = {c['id']: c for c in case['citations']}
    places = {p['id']: p['literal'] for p in case['places']}
    conclusions = {c['id']: c for c in case['conclusions']}
    loss = {'conclusions_by_status': {}, 'relationship_types': {}, 'predicates': {}, 'unlinked_mentions': 0}
    assumed_roles = []

    def count(bucket, key):
        loss[bucket][key] = loss[bucket].get(key, 0) + 1

    def person_of(subject):
        if subject in persons:
            return subject
        mention = mentions.get(subject)
        return mention.get('person_id') if mention else None

    facts = {}          # person id -> [(tag, observation, conclusion)]
    family_facts = {}   # frozenset(person ids) -> [(tag, observation, conclusion)]
    for con in case['conclusions']:
        if con['status'] not in include:
            count('conclusions_by_status', con['status'])
            continue
        for oid in con['observation_ids']:
            obs = observations[oid]
            predicate = obs.get('predicate', '')
            subject = person_of(obs.get('subject_id'))
            if predicate in FAMILY_TAGS and subject and obs.get('object_person_id') in persons:
                family_facts.setdefault(frozenset((subject, obs['object_person_id'])), []).append((FAMILY_TAGS[predicate], obs, con))
            elif predicate in EXPORT_TAGS and subject:
                facts.setdefault(subject, []).append((EXPORT_TAGS[predicate], obs, con))
            elif predicate in EXPORT_TAGS or predicate in FAMILY_TAGS:
                loss['unlinked_mentions'] += 1
            elif predicate not in ('parent', 'spouse') + PARENT_TYPES:
                count('predicates', predicate or 'none')

    couples, children = {}, {}
    for rel in case['relationships']:
        if rel['status'] not in include:
            continue
        con = conclusions.get(rel['conclusion_id'])
        if rel['type'] == 'spouse':
            couples.setdefault(frozenset((rel['from_person_id'], rel['to_person_id'])), []).append(con)
        elif rel['type'] in PARENT_TYPES:
            children.setdefault(rel['to_person_id'], {})[rel['from_person_id']] = con
        else:
            count('relationship_types', rel['type'])
    families = {key: {'spouses': key, 'children': [], 'cons': list(cons), 'facts': []} for key, cons in couples.items()}
    for child, parents in sorted(children.items()):
        key = frozenset(parents)
        family = families.setdefault(key, {'spouses': key, 'children': [], 'cons': [], 'facts': []})
        family['children'].append(child)
        family['cons'].extend(parents.values())
    for key, items in family_facts.items():
        families.setdefault(key, {'spouses': key, 'children': [], 'cons': [], 'facts': []})['facts'].extend(items)

    included = set(facts)
    for family in families.values():
        included |= set(family['spouses']) | set(family['children'])
    included = sorted(p for p in included if p in persons)
    ixref = {pid: f'@I{n}@' for n, pid in enumerate(included, 1)}
    used_sources = []

    def sref(source_id):
        if source_id not in used_sources:
            used_sources.append(source_id)
        return f'@S{used_sources.index(source_id) + 1}@'

    def cite(level, obs):
        out = gedcom_lines(level, 'SOUR', sref(obs['source_id']))
        cit = citations.get(obs.get('citation_id'))
        out += gedcom_lines(level + 1, 'PAGE', cit['locator'] if cit else obs['locator'])
        if cit and cit.get('text'):
            out += gedcom_lines(level + 1, 'DATA') + gedcom_lines(level + 2, 'TEXT', cit['text'])
        return out

    def status_note(level, con):
        note = f"Status: {con['status']}."
        assessment = con.get('evidence_assessment')
        if assessment:
            note += f" Scope: {assessment['scope']} Reviewed {assessment['reviewed_on']}."
        return gedcom_lines(level, 'NOTE', note)

    def fact_lines(tag, obs, con):
        value = obs.get('value')
        out = gedcom_lines(1, tag, value if tag == 'OCCU' and isinstance(value, str) else '')
        when = gedcom_date(value) if isinstance(value, dict) else None
        if when:
            out += gedcom_lines(2, 'DATE', when)
        where = places.get(obs.get('place_id'))
        if where:
            out += gedcom_lines(2, 'PLAC', where)
        if isinstance(value, str) and tag != 'OCCU' and value:
            out += gedcom_lines(2, 'NOTE', value)
        return out + cite(2, obs) + status_note(2, con)

    reviewed_obs = {oid for c in case['conclusions'] if c['status'] in include for oid in c['observation_ids']}

    def sex_of(pid, reviewed_only=True):
        """Sex from the person row or a sex observation; unreviewed ones only guide HUSB/WIFE."""
        if persons[pid].get('sex') in ('M', 'F'):
            return persons[pid]['sex']
        for obs in case['observations']:
            if (obs.get('predicate') == 'sex' and person_of(obs.get('subject_id')) == pid
                    and obs.get('value') in ('M', 'F') and (obs['id'] in reviewed_obs or not reviewed_only)):
                return obs['value']
        return None

    out = ['0 HEAD'] + gedcom_lines(1, 'SOUR', 'GENEALOGY_AGENT_SKILLS') + ['1 GEDC', '2 VERS 5.5.1',
           '2 FORM LINEAGE-LINKED', '1 CHAR UTF-8']
    out += gedcom_lines(1, 'NOTE', f"Private export of case {case['case_id']}: only claims with status "
                        f"{', '.join(include)}, each with its sources. The full case keeps the evidence and its limits.")
    fxref = {}
    ordered = sorted(families.values(), key=lambda f: (sorted(f['spouses']), f['children']))
    for n, family in enumerate(ordered, 1):
        fxref[id(family)] = f'@F{n}@'
    for pid in included:
        out += gedcom_lines(0, 'INDI', xref=ixref[pid]) + gedcom_lines(1, 'NAME', persons[pid]['label'])
        sex = sex_of(pid)
        if sex:
            out += gedcom_lines(1, 'SEX', sex)
        for tag, obs, con in facts.get(pid, []):
            out += fact_lines(tag, obs, con)
        for family in ordered:
            if pid in family['children']:
                out += gedcom_lines(1, 'FAMC', fxref[id(family)])
            if pid in family['spouses']:
                out += gedcom_lines(1, 'FAMS', fxref[id(family)])
    for family in ordered:
        out += gedcom_lines(0, 'FAM', xref=fxref[id(family)])
        slots = {}
        for pid in sorted(family['spouses']):
            role = {'M': 'HUSB', 'F': 'WIFE'}.get(sex_of(pid))
            if not role:
                role = {'M': 'HUSB', 'F': 'WIFE'}.get(sex_of(pid, reviewed_only=False))
                if role:
                    assumed_roles.append({'person_id': pid, 'role': role, 'reason': 'from an unreviewed sex claim'})
            if not role or role in slots:
                role = 'WIFE' if 'HUSB' in slots else 'HUSB'
                assumed_roles.append({'person_id': pid, 'role': role, 'reason': 'sex unknown; GEDCOM 5.5.1 needs HUSB or WIFE'})
            slots[role] = pid
        for role in ('HUSB', 'WIFE'):
            if role in slots:
                out += gedcom_lines(1, role, ixref[slots[role]])
        for child in family['children']:
            out += gedcom_lines(1, 'CHIL', ixref[child])
        for tag, obs, con in family['facts']:
            out += fact_lines(tag, obs, con)
        seen = set()
        for con in family['cons']:
            for oid in con['observation_ids'] if con else []:
                if oid not in seen:
                    seen.add(oid)
                    out += cite(1, observations[oid])
        for con in {c['id']: c for c in family['cons'] if c}.values():
            out += status_note(1, con)
    for n, source_id in enumerate(used_sources, 1):
        source = sources[source_id]
        out += gedcom_lines(0, 'SOUR', xref=f'@S{n}@') + gedcom_lines(1, 'TITL', source['title'])
        where = source.get('uri') or source.get('reference')
        if where:
            out += gedcom_lines(1, 'PUBL', where)
        out += gedcom_lines(1, 'NOTE', f"Source type: {source['source_type']}.")
    out.append('0 TRLR')
    report = {'case_id': case['case_id'], 'gedcom_version': '5.5.1', 'included_statuses': list(include),
              'exported': {'individuals': len(included), 'families': len(ordered),
                           'facts': sum(len(v) for v in facts.values()) + sum(len(f['facts']) for f in ordered),
                           'sources': len(used_sources)},
              'not_exported': loss, 'always_lost': ALWAYS_LOST, 'assumed_roles': assumed_roles,
              'check_before_sharing': [pid for pid in included if persons[pid].get('life_status') != 'deceased'],
              'note': 'Private artifact. People not known to be deceased are listed in check_before_sharing.'}
    return '\n'.join(out) + '\n', report


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check', help='Pre-import check: duplicates, impossible dates, parent/child ages')
    check.add_argument('file')
    imp = sub.add_parser('import', help='Import a GEDCOM file into a new provisional case')
    imp.add_argument('file')
    imp.add_argument('--out', required=True, help='new case file; never overwritten')
    imp.add_argument('--question', help='research question for the case')
    imp.add_argument('--case-id')
    imp.add_argument('--prefix', default='GED', help='ID prefix for imported rows (default GED)')
    exp = sub.add_parser('export', help='Export supported and source_supported claims, with sources, as GEDCOM 5.5.1')
    exp.add_argument('file', help='case JSON')
    exp.add_argument('--out', required=True, help='new .ged file; never overwritten')
    exp.add_argument('--report', help='loss report path (default: OUT.loss.json)')
    exp.add_argument('--include', action='append', choices=['provisional'],
                     help='also export provisional claims (marked as such); off by default')
    args = parser.parse_args(argv)
    try:
        if args.command == 'export':
            case = json.loads(Path(args.file).read_text(encoding='utf-8'))
            text, report = export_case(case, REVIEWED + tuple(args.include or ()))
            out = Path(args.out)
            report_path = Path(args.report) if args.report else out.with_name(out.name + '.loss.json')
            for target in (out, report_path):
                if target.exists():
                    raise ValueError(f'{target} exists; choose a new path')
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open('x', encoding='utf-8') as handle:
                handle.write(text)
            with report_path.open('x', encoding='utf-8') as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
            print(json.dumps({'status': 'created', 'path': str(out), 'loss_report': str(report_path),
                              **report['exported']}, ensure_ascii=False, indent=2))
            return 0
        tree = parse_gedcom(args.file)
        if args.command == 'check':
            report = check_tree(tree)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1 if report['errors'] else 0
        case = import_tree(tree, args.question, args.case_id, args.prefix)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('x', encoding='utf-8') as handle:
            json.dump(case, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        print(json.dumps({'status': 'created', 'path': str(out), 'case_id': case['case_id'],
                          'persons': len(case['persons']), 'relationships': len(case['relationships']),
                          'check_errors': case['import_check']['errors'],
                          'check_warnings': case['import_check']['warnings'],
                          'note': 'Everything imported is provisional; the tree is a claim, not proof.'},
                         ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
