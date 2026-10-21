#!/usr/bin/env python3
"""Small offline front door for the genealogy suite. This does not run an agent."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent
COORDINATOR = ROOT / 'skills/genealogy-mode'
COUNTRY = ROOT / 'skills/genealogy-origin-source-discovery/scripts/country_tools.py'
sys.path.insert(0, str(COORDINATOR / 'scripts'))
from case_tools import validate_case
sys.path.insert(0, str(COUNTRY.parent))
from country_tools import add_filters as add_source_filters


def main():
    # Forward the complete command tail to the appropriate offline helper.
    helpers = {
        'interview': ROOT / 'skills/genealogy-interview/scripts/interview_tools.py',
        'story': ROOT / 'skills/genealogy-narrative/scripts/story_tools.py',
        'reread': COORDINATOR / 'scripts/research_updates.py',
        'project': COORDINATOR / 'scripts/research_updates.py',
        'gedcom': COORDINATOR / 'scripts/gedcom_tools.py',
    }
    if len(sys.argv) > 1 and sys.argv[1] in helpers:
        return subprocess.run([sys.executable, str(helpers[sys.argv[1]]), *([sys.argv[1]] if sys.argv[1] in ('reread', 'project') else []), *sys.argv[2:]]).returncode
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    start = sub.add_parser('start', help='Create a case from one question')
    start.add_argument('--question', required=True); start.add_argument('--out', required=True)
    start.add_argument('--case-id', default=None)
    for name in ('status', 'check'):
        cmd = sub.add_parser(name, help='Show saved progress' if name == 'status' else 'Check evidence references and GPS review records')
        cmd.add_argument('case')
    sub.add_parser('interview', help='Interview state: new, record, status (use interview --help)')
    sub.add_parser('story', help='Story files: brief, check, render (use story --help)')
    sub.add_parser('reread', help='Save a corrected reading and flag dependent findings (reread --help)')
    sub.add_parser('project', help='Generate private fact files and tree notes (project --help)')
    sub.add_parser('gedcom', help='Check a GEDCOM file or import it as a provisional case (gedcom --help)')
    sub.add_parser('countries', help='List country starting points')
    sources = sub.add_parser('sources', help='Suggest official source entry points')
    sources.add_argument('country'); add_source_filters(sources)
    sources.add_argument('--limit', default=3, type=int)
    sources.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'countries':
            return subprocess.run([sys.executable, str(COUNTRY), 'list']).returncode
        if args.command == 'sources':
            command = [sys.executable, str(COUNTRY), 'show', args.country, '--place', args.place,
                       '--region', args.region, '--period', args.period, '--family', args.family, '--limit', str(args.limit)]
            return subprocess.run(command + (['--json'] if args.json else [])).returncode
        if args.command == 'start':
            case = json.loads((COORDINATOR / 'assets/case-template.json').read_text(encoding='utf-8'))
            case['case_id'] = args.case_id or 'C-' + uuid.uuid4().hex[:10]
            case['goal'] = args.question
            case['questions'][0]['text'] = args.question
            errors = validate_case(case, gps=True)
            if errors:
                raise ValueError('; '.join(errors))
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open('x', encoding='utf-8') as handle:
                json.dump(case, handle, ensure_ascii=False, indent=2); handle.write('\n')
            print(f'Created {out}.\nGive your agent this case and any starting records, then ask it to use genealogy-mode.')
            return 0
        case = json.loads(Path(args.case).read_text(encoding='utf-8'))
        errors = validate_case(case, gps=True)
        if args.command == 'check':
            if errors:
                print('Review needed:')
                for error in errors:
                    print('- ' + error)
                return 1
            print('Case checks passed: references and required GPS review records are complete.\nThis check does not establish historical truth or certify GPS compliance.')
            return 0
        print('Question: ' + case['goal'])
        print(f'Saved evidence: {len(case["sources"])} sources, {len(case["observations"])} observations.')
        conclusions = case['conclusions']
        if not conclusions:
            print('Finding: no conclusion recorded yet.')
        for conclusion in conclusions[:3]:
            status = conclusion['status']
            label = {'supported': 'Supported by reviewed evidence', 'rejected': 'Ruled out for this question',
                     'source_supported': 'Source-supported; full proof review pending', 'provisional': 'Working lead', 'unresolved': 'Not yet established', 'superseded': 'Earlier conclusion, revised'}[status]
            if errors and status in ('supported', 'rejected'):
                label = 'Previous conclusion; review still needed'
            print(label + ': ' + conclusion['claim'])
        if len(conclusions) > 3:
            print(f'{len(conclusions) - 3} more conclusions are saved in the case.')
        if errors:
            print(f'Review needed: {len(errors)} issue(s). Run the check command for details.')
        print('Next step: ' + str(case.get('checkpoint', {}).get('next_action') or 'Review the evidence and choose the next useful action.'))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Could not complete: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
