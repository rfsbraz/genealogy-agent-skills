#!/usr/bin/env python3
"""Reference host adapter for a synthetic text-canonical host.

The host keeps its record as JSONL in host/ledger.jsonl, one record per line. Working case
state that the host does not store lives in the sidecar research/cases/<case-id>.json.

    python adapter.py export            prints the case view
    python adapter.py import case.json  writes the case changes back

Synthetic data only. A real host routes import through its own reviewed write path.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LEDGER = HERE / 'host/ledger.jsonl'
SIDECAR_FORMAT = 'genealogy-case-sidecar/1.0'

# Case section -> the host's own record kind. Required sections, plus searches,
# which this host chooses to store itself.
HOST_KINDS = {
    'persons': 'person', 'mentions': 'mention', 'relationships': 'relationship', 'events': 'event',
    'places': 'place', 'sources': 'source', 'citations': 'citation', 'observations': 'reading',
    'conclusions': 'conclusion', 'searches': 'search',
}
SECTION = {kind: section for section, kind in HOST_KINDS.items()}
# Everything else in the case goes to the sidecar.
SIDECAR_SECTIONS = ['goal', 'active_question_id', 'authorization', 'checkpoint', 'questions',
                    'hypotheses', 'tasks', 'repositories', 'holdings', 'correspondence', 'changes']
# Optional fields this host does not store on its own records.
SIDECAR_FIELDS = {'conclusions': ['evidence_assessment']}
ORDER = ['schema_version', 'case_id', 'revision', 'goal', 'active_question_id', 'authorization', 'checkpoint',
         'questions', 'persons', 'mentions', 'relationships', 'events', 'places', 'sources', 'citations',
         'observations', 'hypotheses', 'conclusions', 'searches', 'tasks', 'repositories', 'holdings',
         'correspondence', 'changes']


def sidecar_path(case_id):
    return HERE / 'research/cases' / (case_id + '.json')


def read_ledger():
    rows = [json.loads(line) for line in LEDGER.read_text(encoding='utf-8').splitlines() if line.strip()]
    meta = next(r for r in rows if r['kind'] == 'case')
    return meta, [r for r in rows if r['kind'] != 'case']


def export_case():
    meta, rows = read_ledger()
    case = {'schema_version': meta['schema_version'], 'case_id': meta['case_id'], 'revision': meta['revision']}
    for section in HOST_KINDS:
        case[section] = [r['record'] for r in rows if SECTION[r['kind']] == section]
    sidecar = json.loads(sidecar_path(meta['case_id']).read_text(encoding='utf-8'))
    if sidecar.get('format') != SIDECAR_FORMAT or sidecar.get('case_id') != meta['case_id']:
        raise ValueError('sidecar does not belong to this case')
    case.update(sidecar['sections'])
    for section, records in sidecar['fields'].items():
        by_id = {r['id']: r for r in case[section]}
        for record_id, values in records.items():
            by_id[record_id].update(values)
    return {k: case[k] for k in ORDER}


def import_case(case):
    try:
        meta, _ = read_ledger()
        if meta['case_id'] != case['case_id']:
            raise ValueError('case_id does not match this host record')
    except FileNotFoundError:
        pass
    sidecar = {'format': SIDECAR_FORMAT, 'case_id': case['case_id'],
               'sections': {k: case[k] for k in SIDECAR_SECTIONS}, 'fields': {}}
    lines = [{'kind': 'case', 'case_id': case['case_id'], 'schema_version': case['schema_version'], 'revision': case['revision']}]
    for section, kind in HOST_KINDS.items():
        for record in case[section]:
            record = dict(record)
            for field in SIDECAR_FIELDS.get(section, []):
                if field in record:
                    sidecar['fields'].setdefault(section, {})[record['id']] = {field: record.pop(field)}
            lines.append({'kind': kind, 'record': record})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(''.join(json.dumps(line, ensure_ascii=False, sort_keys=True) + '\n' for line in lines), encoding='utf-8')
    path = sidecar_path(case['case_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'export':
        print(json.dumps(export_case(), ensure_ascii=False, indent=2))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == 'import':
        import_case(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
