#!/usr/bin/env python3
"""Offline country starter lookup. Produces leads, never claims to search archives."""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlparse

DATABASE = Path(__file__).resolve().parents[1] / 'assets' / 'countries'
KINDS = {'repository', 'catalogue', 'request_service', 'civil_authority', 'directory', 'digital_library', 'guide'}
# Record families a source can serve. --family takes one of these; it is not a surname.
RECORD_FAMILIES = ('civil', 'household', 'institutional', 'legal', 'migration', 'military', 'press', 'religious')
QUERY_NOTE = 'Place, region and period fill the search queries; they do not filter the starter sources.'


def normal(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c)).strip()


def index(database=DATABASE):
    return json.loads((database / 'index.json').read_text(encoding='utf-8'))


def read_profile(item, database=DATABASE):
    # Only paths named by validated country codes are accepted, never user paths.
    if not re.fullmatch('[A-Z]{2}', item['code']) or item['path'] != item['code'] + '.json':
        raise ValueError('Invalid country profile path')
    return json.loads((database / item['path']).read_text(encoding='utf-8'))


def lookup(country, database=DATABASE):
    needle = normal(country)
    for item in index(database)['countries']:
        if needle in {normal(s) for s in [item['code'], item['name'], *item['aliases']]}:
            return read_profile(item, database)
    return None


def validate(database=DATABASE):
    errors = []
    seen_codes, seen_sources, seen_aliases = set(), set(), {}
    data = index(database)
    for item in data['countries']:
        code = item['code']
        if code in seen_codes:
            errors.append(f'Duplicate country code: {code}')
        seen_codes.add(code)
        profile = read_profile(item, database)
        for field in ('name', 'native_name', 'languages', 'search_terms', 'first_steps', 'jurisdiction_questions', 'query_templates', 'sources'):
            if not profile.get(field):
                errors.append(f'{code}: missing/empty {field}')
        if profile.get('code') != code or profile.get('starter_status') != 'seed_only':
            errors.append(f'{code}: incorrect identity or starter status')
        if profile.get('name') != item['name'] or profile.get('aliases') != item['aliases']:
            errors.append(f'{code}: index/profile mismatch')
        date.fromisoformat(profile['last_reviewed'])
        for alias in [code, item['name'], *item['aliases']]:
            key = normal(alias)
            if key in seen_aliases and seen_aliases[key] != code:
                errors.append(f'Ambiguous alias: {alias}')
            seen_aliases[key] = code
        for source in profile['sources']:
            sid = source['id']
            if sid in seen_sources or not sid.startswith(code + '-'):
                errors.append(f'{code}: duplicate or foreign source ID {sid}')
            seen_sources.add(sid)
            if source['kind'] not in KINDS:
                errors.append(f'{sid}: unknown role')
            if source['coverage_status'] != 'not_assessed_for_person':
                errors.append(f'{sid}: starter must not claim person-specific coverage')
            for field in ('name', 'purpose', 'record_families', 'access', 'fallback'):
                if not source.get(field):
                    errors.append(f'{sid}: missing {field}')
            for family in source.get('record_families', []):
                if family not in RECORD_FAMILIES:
                    errors.append(f'{sid}: unknown record family {family}')
            check = source['verification']
            date.fromisoformat(check['checked_on'])
            if check['method'] not in ('official_search_result', 'official_page'):
                errors.append(f'{sid}: unknown verification method')
            urls = [source['url'], check['evidence_url']]
            notice = source.get('service_notice')
            if notice:
                date.fromisoformat(notice['observed_on'])
                urls.extend([notice['evidence_url'], notice['fallback_url']])
            for url in urls:
                parsed = urlparse(url)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                    errors.append(f'{sid}: invalid public HTTPS URL')
        for template in profile['query_templates']:
            try:
                template.format(place='PLACE', region='REGION', period='PERIOD')
            except (KeyError, ValueError):
                errors.append(f'{code}: invalid query template')
    return errors


def plan(country, place='', region='', period='', family='', limit=3, database=DATABASE, today=None):
    if limit < 1:
        raise ValueError('limit must be positive')
    if family and family not in RECORD_FAMILIES:
        raise ValueError(f'--family takes a record family, not a surname: {family!r}. Use one of: ' + ', '.join(RECORD_FAMILIES) + '.')
    notes = [QUERY_NOTE] if place or region or period else []
    profile = lookup(country, database)
    if not profile:
        return {'country': country, 'status': 'discovery_required', 'sources': [],
                'next_steps': ['Resolve the event locality and historical jurisdiction from evidence.',
                               'Find official national and regional archive directories in the relevant languages.',
                               'Identify the record creator and custodian; verify collection dates, survival and access.',
                               'Save a sourced country profile and person-specific portfolio.'],
                'queries': [f'{country} {place} {region} official archives genealogy {period}'.strip()],
                'notes': notes + ([f'--family {family} has no effect without a starter profile.'] if family else []),
                'notice': 'No starter profile yet. Continue discovery; do not substitute a neighbouring country or infer origin from a surname.'}
    today = today or date.today()
    entries = profile['sources']
    if family:
        # Relevant record family first. Directories remain useful discovery routes.
        carrying = sum(family in s['record_families'] for s in entries)
        if carrying == 0:
            notes.append(f'--family {family} has no effect: no {profile["name"]} starter source lists it.')
        elif carrying == len(entries):
            notes.append(f'--family {family} has no effect: every {profile["name"]} starter source lists it, so the order is unchanged.')
        entries = sorted(entries, key=lambda s: (family not in s['record_families'], s['kind'] != 'directory'))
    chosen = []
    for source in entries[:limit]:
        source = dict(source)
        checked = date.fromisoformat(source['verification']['checked_on'])
        source['refresh_due'] = today > checked + timedelta(days=90) or bool(source['service_notice'])
        chosen.append(source)
    return {'country': profile['name'], 'code': profile['code'], 'status': 'starter_leads',
            'scope': {'place': place or 'not yet established', 'region': region or 'not yet established',
                      'period': period or 'not yet established', 'record_family': family or 'not yet selected'},
            'sources': chosen, 'remaining_source_count': max(0, len(entries) - len(chosen)),
            'next_steps': profile['first_steps'], 'jurisdiction_questions': profile['jurisdiction_questions'],
            'queries': [q.format(place=place or '[locality]', region=region or '[region]', period=period or '[period]')
                        for q in profile['query_templates']],
            'notes': notes,
            'notice': 'Starting points only. No searches or transactions were performed; verify locality, period, holdings and access at use time.'}


def add_filters(parser):
    parser.add_argument('--place', default='', help='Locality. Fills the search queries; does not filter sources.')
    parser.add_argument('--region', default='', help='Region or district. Fills the search queries; does not filter sources.')
    parser.add_argument('--period', default='', help='Years, for example 1840-1870. Fills the search queries; does not filter sources.')
    parser.add_argument('--family', default='', help='Record family to list first, not a surname. One of: ' + ', '.join(RECORD_FAMILIES) + '.')


def text(result):
    lines = [f'{result["country"]}: where to start', '']
    for source in result['sources']:
        lines += [f'{source["name"]} ({source["kind"].replace("_", " ")})', source['purpose'], source['url']]
        if source['refresh_due']:
            lines.append('Recheck availability before use.')
        lines.append('')
    if 'scope' in result:
        scope = result['scope']
        lines.append(f'Scope: place {scope["place"]}; region {scope["region"]}; period {scope["period"]}; record family {scope["record_family"]}.')
    lines.append('Search queries:')
    lines += ['- ' + q for q in result['queries']]
    lines += result['notes']
    lines.append('Next step: ' + result['next_steps'][0])
    lines.append(result['notice'])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DATABASE)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate')
    ls = sub.add_parser('list'); ls.add_argument('--json', action='store_true')
    show = sub.add_parser('show'); show.add_argument('country')
    add_filters(show)
    show.add_argument('--limit', type=int, default=3); show.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        errors = validate(args.database)
        if errors:
            raise ValueError('; '.join(errors))
        if args.command == 'validate':
            print(json.dumps({'valid': True, 'country_count': len(index(args.database)['countries'])}))
        elif args.command == 'list':
            rows = index(args.database)['countries']
            print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else
                  '\n'.join(f'{r["code"]}: {r["name"]}' for r in rows) + '\nOther countries: discover sources as needed.')
        else:
            result = plan(args.country, args.place, args.region, args.period, args.family, args.limit, args.database)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(text(result))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Country lookup could not complete: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
