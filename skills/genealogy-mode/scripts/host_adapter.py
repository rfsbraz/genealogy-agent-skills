#!/usr/bin/env python3
"""Host adapter contract helpers: split a case into host and sidecar parts, merge them back,
check a sidecar, and run an adapter's export/import round trip. No model or network calls.

See references/host-adapter.md. The contract itself is assets/host-adapter-contract.json.
"""
import argparse
import copy
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from case_tools import validate_case

CONTRACT_PATH = Path(__file__).resolve().parents[1] / 'assets/host-adapter-contract.json'


def load_contract(path=CONTRACT_PATH):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _field_rules(contract):
    """Yield (key, section, field) for each field-level rule such as conclusions.evidence_assessment."""
    for key in contract.get('fields', {}):
        section, field = key.split('.', 1)
        yield key, section, field


def split(case, contract, host_stores=()):
    """Return (host_view, sidecar). host_stores names optional sections or fields the host keeps itself."""
    host_stores = set(host_stores)
    host, sections = {}, {}
    for name, rule in contract['sections'].items():
        if name not in case:
            continue
        keep = rule['class'] == 'required' or (rule['class'] == 'optional' and name in host_stores)
        (host if keep else sections)[name] = copy.deepcopy(case[name])
    fields = {}
    for key, section, field in _field_rules(contract):
        if key in host_stores or section not in host:
            continue
        for record in host[section]:
            if field in record:
                fields.setdefault(section, {})[record['id']] = {field: record.pop(field)}
    sidecar = {'format': contract['sidecar']['format'], 'case_id': case['case_id'], 'sections': sections, 'fields': fields}
    return host, sidecar


def sidecar_errors(sidecar, contract):
    errors = []
    if sidecar.get('format') != contract['sidecar']['format']:
        errors.append('sidecar format must be ' + contract['sidecar']['format'])
    if not isinstance(sidecar.get('case_id'), str) or not sidecar['case_id']:
        errors.append('sidecar needs the case_id')
    for name in sidecar.get('sections', {}):
        rule = contract['sections'].get(name)
        if rule is None:
            errors.append(name + ': not in the contract; classify it before storing it')
        elif rule['class'] == 'required':
            errors.append(name + ': required section owned by the host; it never goes in the sidecar')
    allowed = {key for key, _, _ in _field_rules(contract)}
    for section, records in sidecar.get('fields', {}).items():
        for record_id, values in records.items():
            for field in values:
                if section + '.' + field not in allowed:
                    errors.append(section + '.' + field + ' on ' + record_id + ': host-owned field; it never goes in the sidecar')
    return errors


def merge(host, sidecar, contract):
    """Rebuild the case view from the host export and the sidecar."""
    errors = sidecar_errors(sidecar, contract)
    if host.get('case_id') != sidecar.get('case_id'):
        errors.append('host and sidecar disagree on case_id')
    both = sorted(set(host) & set(sidecar.get('sections', {})))
    if both:
        errors.append('sections in both host and sidecar (two authorities): ' + ', '.join(both))
    if errors:
        raise ValueError('; '.join(errors))
    case = copy.deepcopy(host)
    case.update(copy.deepcopy(sidecar.get('sections', {})))
    for section, records in sidecar.get('fields', {}).items():
        by_id = {r['id']: r for r in case.get(section, [])}
        for record_id, values in records.items():
            if record_id not in by_id:
                raise ValueError('sidecar field for unknown ' + section + ' record ' + record_id)
            for field, value in values.items():
                if field in by_id[record_id]:
                    raise ValueError(section + '.' + field + ' on ' + record_id + ' is in both host and sidecar')
                by_id[record_id][field] = copy.deepcopy(value)
    return case


def _export(command, cwd):
    run = subprocess.run(shlex.split(command), cwd=cwd, capture_output=True, text=True)
    if run.returncode:
        raise ValueError('export failed: ' + run.stderr.strip())
    return json.loads(run.stdout)


def case_errors(case, contract):
    errors = ['unclassified section ' + k + ': add it to the contract' for k in case if k not in contract['sections']]
    errors += ['missing section ' + k for k in contract['sections'] if k not in case]
    if case.get('schema_version') not in contract['case_schema_versions']:
        errors.append('case schema_version ' + str(case.get('schema_version')) + ' is not covered by this contract')
    return errors + validate_case(case)


def check(export_command, import_command, sidecar_path=None, cwd='.', contract=None):
    """Export, import that export unchanged, export again. The two exports must be identical."""
    contract = contract or load_contract()
    first = _export(export_command, cwd)
    errors = case_errors(first, contract)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'case.json'
        path.write_text(json.dumps(first, ensure_ascii=False, indent=2), encoding='utf-8')
        run = subprocess.run(shlex.split(import_command) + [str(path)], cwd=cwd, capture_output=True, text=True)
        if run.returncode:
            errors.append('import failed: ' + run.stderr.strip())
    second = _export(export_command, cwd)
    differences = sorted(k for k in set(first) | set(second) if first.get(k) != second.get(k))
    if sidecar_path:
        sidecar_file = Path(cwd) / sidecar_path
        if sidecar_file.exists():
            errors += sidecar_errors(json.loads(sidecar_file.read_text(encoding='utf-8')), contract)
    return {'contract': contract['contract'] + '/' + contract['version'], 'case_id': first.get('case_id'),
            'round_trip': 'identical' if not differences else 'different',
            'changed_sections': differences, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    chk = sub.add_parser('check', help='Run export, import unchanged, export again')
    chk.add_argument('--export', required=True, help='Command that prints the case view JSON')
    chk.add_argument('--import', dest='import_', required=True, help='Command that takes a case JSON path as its last argument')
    chk.add_argument('--sidecar', help='Sidecar path to check after import, relative to the working directory')
    side = sub.add_parser('sidecar-check', help='Check that a sidecar holds no host-owned facts')
    side.add_argument('file')
    args = parser.parse_args()
    try:
        if args.command == 'check':
            result = check(args.export, args.import_, args.sidecar)
            ok = result['round_trip'] == 'identical' and not result['errors']
        else:
            errors = sidecar_errors(json.loads(Path(args.file).read_text(encoding='utf-8')), load_contract())
            result, ok = {'errors': errors}, not errors
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
