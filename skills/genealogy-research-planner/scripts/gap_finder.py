#!/usr/bin/env python3
"""Tree gap finder: list the records that should exist for people in a case, and where to look.

Standard library only, no network. It reads a case (the coordinator's JSON case) and a folder of
per-country source registry files (assets/source-registry.schema.json), and writes ranked search
candidates. It never searches, orders or changes the case. Commands:

  gaps CASE --registry DIR [--person ID ...] [--mode detail|expand] [--json]
  validate-registry PATH
  learn CASE --registry DIR --search SEARCH-ID
"""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
import tempfile

RECORD_TYPES = {'birth', 'baptism', 'marriage', 'death', 'burial', 'census', 'foundling', 'newspaper',
                'probate', 'military', 'migration', 'other'}
ROUTES = {'online_images', 'online_index', 'catalogue_only', 'request', 'onsite'}
COSTS = {'free', 'account', 'paid'}
METHODS = {'catalogue_search', 'index_search', 'browse_by_book', 'order_certificate', 'onsite_visit', 'write_to_custodian'}
FACTS = {'birth': 'birth', 'birth_date': 'birth', 'baptism': 'baptism', 'baptism_date': 'baptism',
         'christening': 'baptism', 'death': 'death', 'death_date': 'death', 'burial': 'burial',
         'burial_date': 'burial', 'marriage': 'marriage', 'marriage_date': 'marriage'}
REVIEWED = ('supported', 'source_supported')
CLOSED = ('rejected', 'superseded')
SETTLED_OUTCOMES = ('no_match', 'found')
APPROX_SLACK = 5
MIN_MARRIAGE_AGE = 14
MIN_PARENT_AGE = 15
MAX_PARENT_AGE = 50
DEATH_EXPECTED_AFTER = 110
LIFESPAN = 100
MODE_WEIGHT = {('expand', 'parents'): 3.0, ('expand', 'children'): 2.0}


# ---------------------------------------------------------------- registry

def validate_registry(data):
    """Errors for one registry file; mirrors assets/source-registry.schema.json."""
    errors = []

    def need(obj, keys, where):
        for key in keys:
            if key not in obj:
                errors.append(f'{where}: {key} is required')

    def years(obj, where):
        for key in ('from_year', 'to_year'):
            if obj.get(key) is not None and (not isinstance(obj.get(key), int) or isinstance(obj.get(key), bool)):
                errors.append(f'{where}: {key} must be a whole year or null')
        if isinstance(obj.get('from_year'), int) and isinstance(obj.get('to_year'), int) and obj['from_year'] > obj['to_year']:
            errors.append(f'{where}: from_year is after to_year')

    def types(value, where):
        if not isinstance(value, list) or not value:
            errors.append(f'{where}: record_types must list at least one type')
        elif set(value) - RECORD_TYPES:
            errors.append(f'{where}: unknown record_types {sorted(set(value) - RECORD_TYPES)}')

    def places(value, where):
        if not isinstance(value, list) or not value or not all(isinstance(p, str) and p.strip() for p in value):
            errors.append(f'{where}: places must list at least one place name or "*"')

    if not isinstance(data, dict):
        return ['registry must be a JSON object']
    need(data, ('schema_version', 'code', 'name', 'place_names', 'sources'), 'registry')
    if data.get('schema_version') not in (None, '1.0'):
        errors.append('registry: schema_version must be "1.0"')
    if not data.get('place_names'):
        errors.append('registry: place_names must list at least one name')
    seen = set()
    for i, source in enumerate(data.get('sources') or []):
        where = f"sources[{i}] {source.get('id', '?')}"
        need(source, ('id', 'name', 'record_types', 'coverage', 'access', 'query'), where)
        if source.get('id') in seen:
            errors.append(f'{where}: duplicate source id')
        seen.add(source.get('id'))
        types(source.get('record_types'), where)
        for j, cov in enumerate(source.get('coverage') or []):
            need(cov, ('from_year', 'to_year', 'places'), f'{where} coverage[{j}]')
            years(cov, f'{where} coverage[{j}]')
            places(cov.get('places'), f'{where} coverage[{j}]')
            if 'record_types' in cov:
                types(cov['record_types'], f'{where} coverage[{j}]')
        if not source.get('coverage'):
            errors.append(f'{where}: coverage must list at least one range')
        access = source.get('access') or {}
        if access.get('route') not in ROUTES:
            errors.append(f'{where}: access route must be one of {sorted(ROUTES)}')
        if access.get('cost') not in COSTS:
            errors.append(f'{where}: access cost must be one of {sorted(COSTS)}')
        query = source.get('query') or {}
        if query.get('method') not in METHODS:
            errors.append(f'{where}: query method must be one of {sorted(METHODS)}')
        if not str(query.get('how', '')).strip():
            errors.append(f'{where}: query how is required')
        for j, gap in enumerate(source.get('known_gaps') or []):
            need(gap, ('record_types', 'places', 'from_year', 'to_year', 'note'), f'{where} known_gaps[{j}]')
            types(gap.get('record_types'), f'{where} known_gaps[{j}]')
            places(gap.get('places'), f'{where} known_gaps[{j}]')
            years(gap, f'{where} known_gaps[{j}]')
    return errors


def registry_files(path):
    path = Path(path)
    return sorted(path.glob('*.json')) if path.is_dir() else [path]


def load_registry(path):
    countries = []
    for file in registry_files(path):
        data = json.loads(file.read_text(encoding='utf-8'))
        errors = validate_registry(data)
        if errors:
            raise ValueError(f'{file.name}: ' + '; '.join(errors[:5]))
        data['_file'] = str(file)
        countries.append(data)
    return countries


# ---------------------------------------------------------------- case reading

def year_bounds(value):
    """(low, high) years from a case date object or literal; None when there is no usable year."""
    if value is None:
        return None
    if isinstance(value, dict):
        lo = hi = None
        if value.get('earliest') or value.get('latest'):
            lo = int(str(value['earliest'])[:4]) if value.get('earliest') else None
            hi = int(str(value['latest'])[:4]) if value.get('latest') else None
        elif value.get('date'):
            lo = hi = int(str(value['date'])[:4])
        elif value.get('alternatives'):
            ys = [a['year'] for a in value['alternatives'] if isinstance(a.get('year'), int)]
            lo, hi = (min(ys), max(ys)) if ys else (None, None)
        literal = str(value.get('literal', ''))
        kind = str(value.get('kind', ''))
    else:
        literal, kind, lo, hi = str(value), '', None, None
    if lo is None and hi is None:
        found = [int(y) for y in re.findall(r'(?<!\d)(1\d{3}|20\d{2})(?!\d)', literal)]
        if not found:
            return None
        lo, hi = min(found), max(found)
    lo = hi if lo is None else lo
    hi = lo if hi is None else hi
    if 'approx' in kind or 'estimat' in kind or re.match(r'^\s*(ABT|CAL|EST|about|circa|c\.)\b', literal, re.I):
        lo, hi = lo - APPROX_SLACK, hi + APPROX_SLACK
    return lo, hi


class Tree:
    """People, their facts and links, read from the case without changing it."""

    def __init__(self, case):
        self.case = case
        self.persons = {p['id']: p for p in case['persons']}
        mentions = {m['id']: m.get('person_id') for m in case['mentions']}
        places = {p['id']: p for p in case['places']}
        superseded = {o['supersedes'] for o in case['observations'] if o.get('supersedes')}
        status = {}
        for con in case['conclusions']:
            for oid in con['observation_ids']:
                status.setdefault(oid, set()).add(con['status'])
        self.facts = {}
        for obs in case['observations']:
            kind = FACTS.get(obs.get('predicate', ''))
            if not kind or obs['id'] in superseded:
                continue
            statuses = status.get(obs['id'], set())
            if statuses and statuses <= set(CLOSED):
                continue
            subject = obs.get('subject_id')
            subject = subject if subject in self.persons else mentions.get(subject)
            if subject not in self.persons:
                continue
            place = places.get(obs.get('place_id'))
            fact = {'kind': kind, 'observation_id': obs['id'], 'years': year_bounds(obs.get('value')),
                    'place': place['literal'] if place else None, 'place_country': place.get('country') if place else None,
                    'sourced': bool(statuses & set(REVIEWED)), 'with': obs.get('object_person_id')}
            self.facts.setdefault(subject, []).append(fact)
        self.parents, self.children, self.spouses = {}, {}, {}
        for rel in case['relationships']:
            if rel['status'] in CLOSED:
                continue
            a, b = rel['from_person_id'], rel['to_person_id']
            if rel['type'] in ('parent', 'biological_parent'):
                self.parents.setdefault(b, set()).add(a)
                self.children.setdefault(a, set()).add(b)
            elif rel['type'] == 'spouse':
                self.spouses.setdefault(a, set()).add(b)
                self.spouses.setdefault(b, set()).add(a)

    def of(self, pid, *kinds):
        return [f for f in self.facts.get(pid, []) if f['kind'] in kinds]

    def bounds(self, pid, *kinds):
        found = [f['years'] for f in self.of(pid, *kinds) if f['years']]
        return (min(y[0] for y in found), max(y[1] for y in found)) if found else None

    def birth(self, pid):
        return self.bounds(pid, 'birth', 'baptism')

    def place(self, pid, *kinds):
        for f in self.of(pid, *kinds):
            if f['place']:
                return f['place'], f['place_country']
        return None, None


# ---------------------------------------------------------------- matching

def _norm(text):
    return ' '.join(str(text).casefold().split())


def _place_matches(names, place):
    return any(n == '*' or _norm(n) in _norm(place) for n in names)


def country_for(place, place_country, countries):
    for country in countries:
        if place_country and place_country == country['code']:
            return country
    for country in countries:
        if place and _place_matches(country['place_names'], place):
            return country
    return None


def _overlap(a_lo, a_hi, b_lo, b_hi):
    return (b_hi is None or a_lo <= b_hi) and (b_lo is None or a_hi >= b_lo)


def _span(lo, hi):
    return f"{lo if lo is not None else 'the start'} to {hi if hi is not None else 'today'}"


def match_sources(country, record_types, years, place):
    """Registry sources that hold one of the record types for this place and period, with reasons."""
    lo, hi = years
    matches, excluded = [], []
    for source in country['sources']:
        for cov in source['coverage']:
            kinds = set(cov.get('record_types', source['record_types'])) & set(source['record_types']) & set(record_types)
            if not kinds or not _place_matches(cov['places'], place) or not _overlap(lo, hi, cov['from_year'], cov['to_year']):
                continue
            gaps = [g for g in source.get('known_gaps', [])
                    if set(g['record_types']) & kinds and _place_matches(g['places'], place)
                    and (g['from_year'] is None or g['from_year'] <= lo) and (g['to_year'] is None or g['to_year'] >= hi)]
            if gaps:
                excluded.append({'id': source['id'], 'reason': gaps[0]['note']})
                break
            where = 'every place' if '*' in cov['places'] else ', '.join(cov['places'])
            matches.append({
                'id': source['id'], 'name': source['name'], 'record_types': sorted(kinds),
                'why': f"holds {', '.join(sorted(kinds))} for {where}, {_span(cov['from_year'], cov['to_year'])}",
                'access': source['access']['route'], 'cost': source['access']['cost'],
                'query': source['query'], 'needs_approval': source['access']['cost'] == 'paid',
                **({'url': source['url']} if source.get('url') else {})})
            break
    return matches, excluded


def _settles(search, source_id, kinds, persons, years):
    if search.get('source_id') != source_id or search.get('outcome') not in SETTLED_OUTCOMES:
        return False
    types = set(search.get('record_types') or ([search['record_type']] if search.get('record_type') else []))
    span = search.get('years') or []
    return (bool(types & set(kinds)) and bool(set(search.get('person_ids') or []) & set(persons))
            and len(span) == 2 and span[0] <= years[0] and span[1] >= years[1])


def _attempts(search, source_id, kinds, persons, years):
    span = search.get('years') or []
    types = set(search.get('record_types') or [])
    return (search.get('source_id') == source_id and search.get('outcome') not in SETTLED_OUTCOMES
            and bool(types & set(kinds)) and bool(set(search.get('person_ids') or []) & set(persons))
            and len(span) == 2 and _overlap(years[0], years[1], span[0], span[1]))


# ---------------------------------------------------------------- candidates

def find_gaps(case, countries, person_ids=None, modes=('detail', 'expand'), today=None):
    today = today or date.today()
    tree = Tree(case)
    searches = case.get('searches', [])
    wanted = set(person_ids or tree.persons)
    candidates, skipped = [], []

    def label(pid):
        return tree.persons[pid]['label']

    def propose(mode, kind, persons, expected, record_types, years, place, place_country, extra=None, targets=None):
        """targets: [(record_types, years[, place, country])] when one candidate covers several records."""
        targets = [tuple(t) + (place, place_country)[len(t) - 2:] for t in (targets or [(record_types, years)])]
        targets = [t for t in targets if t[1]]
        span = (min(t[1][0] for t in targets), max(t[1][1] for t in targets)) if targets else None
        base = {'mode': mode, 'kind': kind, 'person_ids': sorted(persons), 'expected_record': expected,
                'years': list(span) if span else None, 'place': place}
        base['id'] = 'GAP-' + '-'.join([mode, kind] + base['person_ids'])
        if not targets:
            skipped.append({**base, 'reason': 'no date to search from; record or estimate one first'})
            return
        targets = [t for t in targets if t[2] and country_for(t[2], t[3], countries)]
        country = country_for(place, place_country, countries) or (country_for(targets[0][2], targets[0][3], countries) if targets else None)
        if not targets or not country:
            skipped.append({**base, 'reason': 'no place, or no registry for its country' if place else 'no place to search'})
            return
        sources, excluded, settled = [], [], []
        for types, when, where, where_country in targets:
            found, out = match_sources(country_for(where, where_country, countries), types, when, where)
            excluded += out
            for source in found:
                hit = next((x for x in searches if _settles(x, source['id'], source['record_types'], persons, when)), None)
                if hit:
                    settled.append({'id': source['id'], 'record_types': source['record_types'],
                                    'search_id': hit['id'], 'outcome': hit['outcome']})
                    continue
                source['years'] = list(when)
                source['place'] = where
                source['earlier_attempts'] = [{'search_id': x['id'], 'outcome': x['outcome'], 'coverage': x.get('coverage')}
                                              for x in searches if _attempts(x, source['id'], source['record_types'], persons, when)]
                sources.append(source)
        base.update(country=country['code'], excluded_sources=excluded, already_searched=settled)
        if not sources:
            reasons = [f"already searched: {x['search_id']} ({x['outcome']})" for x in settled]
            reasons += [f"{e['id']}: {e['reason']}" for e in excluded]
            skipped.append({**base, 'reason': '; '.join(reasons) or 'no registry source holds this record type here and then'})
            return
        score = MODE_WEIGHT.get((mode, kind), 1.0)
        if any(x['cost'] == 'free' and x['access'].startswith('online') for x in sources):
            score += 0.5
        if all(x['needs_approval'] for x in sources):
            score -= 0.5
        candidates.append({**base, **(extra or {}), 'sources': sources, 'priority': score,
                           'needs_approval': any(x['needs_approval'] for x in sources)})

    def child_place(pids):
        for parent in pids:
            for child in sorted(tree.children.get(parent, ())):
                place = tree.place(child, 'baptism', 'birth')
                if place[0]:
                    return place
        return None, None

    def marriage_window(a, b):
        births = [tree.birth(p) for p in (a, b)]
        lows = [y[0] + MIN_MARRIAGE_AGE for y in births if y]
        kids = [tree.birth(c) for c in tree.children.get(a, set()) & tree.children.get(b, set())]
        kids = [k for k in kids if k]
        if not lows and not kids:
            return None
        lo = max(lows) if lows else min(k[0] for k in kids) - (MAX_PARENT_AGE - MIN_MARRIAGE_AGE)
        hi = min(k[1] for k in kids) if kids else (min(y[1] for y in births if y) + MAX_PARENT_AGE)
        return (lo, max(lo, hi))

    if 'detail' in modes:
        for pid in sorted(wanted):
            if pid not in tree.persons:
                continue
            births = tree.of(pid, 'birth', 'baptism')
            if not any(f['sourced'] for f in births):
                years = tree.birth(pid)
                if not years:
                    kids = [tree.birth(c) for c in tree.children.get(pid, ())]
                    kids = [k for k in kids if k]
                    if kids:
                        years = (min(k[0] for k in kids) - MAX_PARENT_AGE, max(k[1] for k in kids) - MIN_PARENT_AGE)
                place, country = tree.place(pid, 'baptism', 'birth')
                propose('detail', 'birth', [pid], f'birth or baptism record of {label(pid)}', ['birth', 'baptism'],
                        years, place, country)
            deaths = tree.of(pid, 'death', 'burial')
            birth = tree.birth(pid)
            if not any(f['sourced'] for f in deaths) and (deaths or (birth and birth[0] + DEATH_EXPECTED_AFTER <= today.year)):
                years = tree.bounds(pid, 'death', 'burial')
                if not years and birth:
                    alive = [birth[0]] + [tree.birth(c)[0] for c in tree.children.get(pid, ()) if tree.birth(c)]
                    years = (max(alive), min(birth[1] + LIFESPAN, today.year))
                place, country = tree.place(pid, 'death', 'burial')
                if not place:
                    place, country = tree.place(pid, 'baptism', 'birth')
                propose('detail', 'death', [pid], f'death or burial record of {label(pid)}', ['death', 'burial'],
                        years, place, country)
        couples = sorted({tuple(sorted((a, b))) for a, spouses in tree.spouses.items() for b in spouses
                          if a in wanted or b in wanted})
        for a, b in couples:
            facts = [f for f in tree.of(a, 'marriage') + tree.of(b, 'marriage') if f['with'] in (a, b)]
            if any(f['sourced'] for f in facts):
                continue
            years = tree.bounds(a, 'marriage') if facts else marriage_window(a, b)
            place, country = next(((f['place'], f['place_country']) for f in facts if f['place']), (None, None))
            if not place:
                place, country = child_place((a, b))
            propose('detail', 'marriage', [a, b], f'marriage record of {label(a)} and {label(b)}', ['marriage'],
                    years, place, country)

    if 'expand' in modes:
        for pid in sorted(wanted):
            if pid not in tree.persons or tree.parents.get(pid):
                continue
            # Baptism and marriage records often name the parents.
            place, country = tree.place(pid, 'baptism', 'birth')
            if not place:
                place, country = child_place([pid])
            targets = [(['birth', 'baptism'], tree.birth(pid))]
            for spouse in sorted(tree.spouses.get(pid, ())):
                facts = [f for f in tree.of(pid, 'marriage') + tree.of(spouse, 'marriage') if f['with'] in (pid, spouse) and f['place']]
                where = (facts[0]['place'], facts[0]['place_country']) if facts else child_place((pid, spouse))
                if not where[0]:
                    where = (place, country)
                targets.append((['marriage'], marriage_window(pid, spouse), *where))
            propose('expand', 'parents', [pid], f'a record naming the parents of {label(pid)}', None, None,
                    place, country, targets=targets)
        couples = sorted({tuple(sorted((a, b))) for a, spouses in tree.spouses.items() for b in spouses
                          if a in wanted or b in wanted})
        for a, b in couples:
            births = [tree.birth(p) for p in (a, b) if tree.birth(p)]
            if not births:
                continue
            lo = max(y[0] + MIN_PARENT_AGE for y in births)
            hi = min(y[1] + MAX_PARENT_AGE for y in births)
            place, country = child_place((a, b))
            if not place:
                place, country = tree.place(a, 'marriage')
            known = sorted(tree.children.get(a, set()) & tree.children.get(b, set()))
            propose('expand', 'children', [a, b], f'baptisms or births of children of {label(a)} and {label(b)}',
                    ['birth', 'baptism'], (lo, max(lo, hi)), place, country, {'known_children': known})

    candidates.sort(key=lambda c: (-c['priority'], c['id']))
    skipped.sort(key=lambda c: c['id'])
    return {'case_id': case['case_id'], 'candidates': candidates, 'skipped': skipped,
            'registry': [c['code'] for c in countries],
            'scope': ('Search suggestions from the tree and the registry. They say where a record may be, not '
                      'that it exists; paid sources need approval and are never ordered by this helper.')}


# ---------------------------------------------------------------- learning

def learn(case, registry_dir, search_id, today=None):
    """Copy a coverage gap the researcher recorded on a search into that source's known_gaps."""
    search = next((s for s in case.get('searches', []) if s['id'] == search_id), None)
    if not search:
        raise ValueError(f'no search {search_id} in the case')
    gap = search.get('coverage_gap')
    if not gap or not search.get('source_id'):
        raise ValueError(f'{search_id} has no coverage_gap and source_id; record what is missing before learning it')
    for file in registry_files(registry_dir):
        data = json.loads(file.read_text(encoding='utf-8'))
        source = next((s for s in data.get('sources', []) if s['id'] == search['source_id']), None)
        if not source:
            continue
        known = source.setdefault('known_gaps', [])
        if any(g.get('learned_from') == search_id for g in known):
            return {'status': 'already recorded', 'source_id': source['id'], 'file': str(file)}
        entry = {k: gap[k] for k in ('record_types', 'places', 'from_year', 'to_year', 'note')}
        entry.update(learned_from=search_id, learned_on=(today or date.today()).isoformat())
        known.append(entry)
        errors = validate_registry(data)
        if errors:
            raise ValueError('the learned gap would make the registry invalid: ' + '; '.join(errors[:3]))
        fd, tmp = tempfile.mkstemp(dir=file.parent, prefix=file.name, suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(tmp, file)
        return {'status': 'learned', 'source_id': source['id'], 'file': str(file), 'gap': entry}
    raise ValueError(f"no registry source {search['source_id']} in {registry_dir}")


# ---------------------------------------------------------------- CLI

def render(result):
    lines = [f"{len(result['candidates'])} search candidates, {len(result['skipped'])} skipped. {result['scope']}"]
    for c in result['candidates']:
        years = f"{c['years'][0]}-{c['years'][1]}"
        lines.append(f"\n[{c['priority']:.1f}] {c['mode']}: {c['expected_record']}, {years}, {c['place']}")
        if c.get('known_children'):
            lines.append(f"  known children: {', '.join(c['known_children'])}")
        for s in c['sources']:
            flag = ' (paid: ask before ordering)' if s['needs_approval'] else ' (needs an account)' if s['cost'] == 'account' else ''
            at = f" at {s['place']}" if s.get('place') and s['place'] != c['place'] else ''
            lines.append(f"  - {s['name']}{flag}{at}, {s['years'][0]}-{s['years'][1]}: {s['why']}. {s['query']['how']}")
            for a in s.get('earlier_attempts', []):
                lines.append(f"    earlier attempt {a['search_id']}: {a['outcome']}, {a['coverage']}")
        for s in c['already_searched']:
            lines.append(f"  not repeated: {s['id']} (search {s['search_id']}, {s['outcome']})")
    for s in result['skipped']:
        lines.append(f"\nskipped {s['mode']}: {s['expected_record']}: {s['reason']}")
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    gaps = sub.add_parser('gaps', help='List search candidates for people in a case')
    gaps.add_argument('case')
    gaps.add_argument('--registry', required=True, help='registry folder or file')
    gaps.add_argument('--person', action='append', help='only this person ID (repeatable)')
    gaps.add_argument('--mode', action='append', choices=['detail', 'expand'], help='default: both')
    gaps.add_argument('--json', action='store_true')
    val = sub.add_parser('validate-registry', help='Check registry files against the schema rules')
    val.add_argument('path')
    lrn = sub.add_parser('learn', help="Record a search's coverage_gap in the registry")
    lrn.add_argument('case')
    lrn.add_argument('--registry', required=True)
    lrn.add_argument('--search', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate-registry':
            report = {str(f): validate_registry(json.loads(f.read_text(encoding='utf-8'))) for f in registry_files(args.path)}
            print(json.dumps({'valid': not any(report.values()), 'files': report}, ensure_ascii=False, indent=2))
            return 1 if any(report.values()) else 0
        case = json.loads(Path(args.case).read_text(encoding='utf-8'))
        if args.command == 'learn':
            print(json.dumps(learn(case, args.registry, args.search), ensure_ascii=False, indent=2))
            return 0
        result = find_gaps(case, load_registry(args.registry), args.person, tuple(args.mode or ('detail', 'expand')))
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
