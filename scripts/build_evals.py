#!/usr/bin/env python3
"""Write the claude plugin eval suites under evals/.

Two suites share the directory. Cases named trigger-* check which skill a
plain request loads. Cases named quality-* are generated from the synthetic
benchmark in evaluation/genealogy-evaluation, so the answer keys stay the
single source of truth. Run with --check to confirm the files on disk match.

This script never calls a model. Running the suite does; see docs/VALIDATION.md.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / 'evals'
BENCH = ROOT / 'evaluation' / 'genealogy-evaluation' / 'assets' / 'benchmark'
AUTO = ('genealogy-mode', 'genealogy-interview', 'genealogy-narrative')
SKILL = r'"skill"\s*:\s*"(?:[\w-]+:)?'
SPECIALIST = SKILL + r'genealogy-(?!mode"|interview"|narrative")[\w-]+"'
ANY_GENEALOGY = SKILL + r'(?:genealogy-(?:mode|interview|narrative)|story|tree)"'
READ_TOOLS = ['Skill', 'Read', 'Glob', 'Grep']

# (name, expected skill or None, prompt). None marks a near miss.
TRIGGERS = [
    ('01-parish-record', 'genealogy-mode',
     'My great-grandmother was baptised in Viseu, Portugal, around 1890. Where would that record be, and how do I find it?'),
    ('02-unknown-parents', 'genealogy-mode',
     "I'm trying to find out who my great-grandfather's parents were. He was born somewhere in Galicia around 1870 and emigrated to Buenos Aires."),
    ('03-family-history-start', 'genealogy-mode',
     'Can you help me research my family history? My grandmother came from County Cork and I only know her maiden name.'),
    ('04-latin-marriage', 'genealogy-mode',
     "I have a photo of an 1850s parish marriage entry written in Latin. Help me read it and work out who the bride's parents were."),
    ('05-proof-question', 'genealogy-mode',
     "Is a single baptism record enough to prove that Joana is Tome's daughter, or do I need more evidence?"),
    ('06-census-conflict', 'genealogy-mode',
     'Two censuses give my ancestor different birth years, 1861 and 1866. How should I decide which one to trust for my family tree?'),
    ('07-interview-start', 'genealogy-interview',
     "I'd like to start my family tree. Interview me about my family, one question at a time."),
    ('08-tree-command', 'genealogy-interview', '/genealogy:tree start'),
    ('09-life-story', 'genealogy-narrative',
     "Write my great-great-grandmother Beatriz's life as a short family story from what we know: born 1884 in a fishing village, married at 23, worked as a seamstress."),
    ('10-story-command', 'genealogy-narrative', '/genealogy:story Beatriz'),
    ('11-tree-data-structure', None,
     'Write a Python class for a family tree with add_child and find_ancestors methods, plus a couple of unit tests.'),
    ('12-dna-kit', None, 'Which DNA kit is better value right now, AncestryDNA or 23andMe? I only care about price.'),
    ('13-kernel-lineage', None, 'Explain the genealogy of the Linux kernel: how does it relate to Unix and Minix?'),
    ('14-git-tree', None, 'Draw an ASCII git commit graph for a repo with two feature branches merged back into main.'),
    ('15-word-origin', None, 'What does the word "genealogy" mean, and where does it come from?'),
    ('16-dragon-story', None, 'Write a short bedtime story about a dragon who collects family heirlooms.'),
    ('17-job-interview', None, 'Run a mock software engineering job interview with me. Ask one question at a time.'),
    ('18-inheritance-law', None, 'Summarise how inheritance between siblings works under current Portuguese law.'),
    ('19-family-reunion', None, 'Plan a two-day family reunion in Lisbon for 12 people, including two toddlers.'),
    ('20-react-tree', None, 'My React component tree re-renders too often. How do I find which parent causes it?'),
]


def rx_escape(text):
    """Escape for a JavaScript regex without the identity escapes that unicode mode rejects."""
    return re.sub(r'([.^$*+?()\[\]{}|\\/])', r'\\\1', text)


def quote(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return '[' + ', '.join(quote(v) for v in value) + ']'
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z][\w.-]*', value):
        return value
    return "'" + str(value).replace("'", "''") + "'"


def frontmatter(meta, body=''):
    lines = ['---'] + [f'{k}: {quote(v)}' for k, v in meta.items()] + ['---', '']
    return '\n'.join(lines) + (body.rstrip('\n') + '\n' if body else '')


def _scalar(text):
    text = text.strip()
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("''", "'")
    if text.startswith('[') and text.endswith(']'):
        inner = text[1:-1].strip()
        return [_scalar(x) for x in re.findall(r"'(?:[^']|'')*'|[^,]+", inner)] if inner else []
    if text in ('true', 'false'):
        return text == 'true'
    if re.fullmatch(r'-?\d+', text):
        return int(text)
    return text


def read_frontmatter(text):
    """Parse the flat frontmatter this script writes. Not a general YAML parser."""
    if not text.startswith('---\n'):
        raise ValueError('missing frontmatter')
    head, _, body = text[4:].partition('\n---\n')
    meta = {}
    for line in head.splitlines():
        key, sep, value = line.partition(':')
        if not sep or not re.fullmatch(r'[a-z_]+', key):
            raise ValueError(f'unsupported frontmatter line: {line!r}')
        meta[key] = _scalar(value)
    return meta, body


def trigger_files(name, skill, prompt):
    tags = ['trigger', 'should-trigger' if skill else 'near-miss']
    files = {'prompt.md': frontmatter({
        'description': (f'Should load {skill}.' if skill else 'Near miss: no genealogy skill should load.'),
        'tags': tags, 'max_turns': 6, 'timeout_seconds': 180, 'allowed_tools': READ_TOOLS,
    }, prompt)}
    files['graders/no-specialist-skill.md'] = frontmatter({
        'type': 'tool_used', 'tool': 'Skill', 'input_match': SPECIALIST, 'min': 0, 'max': 0, 'arm': 'both'})
    if skill:
        files['graders/fires.md'] = frontmatter({
            'type': 'tool_used', 'tool': 'Skill', 'input_match': SKILL + rx_escape(skill) + '"', 'min': 1, 'weight': 3})
    else:
        files['graders/does-not-fire.md'] = frontmatter({
            'type': 'tool_used', 'tool': 'Skill', 'input_match': ANY_GENEALOGY, 'min': 0, 'max': 0, 'weight': 3, 'arm': 'both'})
    return files


def value_pattern(value):
    if isinstance(value, list):
        return r'\[\s*' + r'\s*,\s*'.join(value_pattern(v) for v in value) + r'\s*\]'
    if isinstance(value, str):
        return '"' + rx_escape(value) + '"'
    return json.dumps(value) + r'(?![\w.])'


def quality_files(gold, task, sources):
    case_id = gold['case_id']
    ids = '|'.join(rx_escape(i) for i in gold['allowed_source_ids'])
    ref = f'"(?:{ids})"'
    body = '\n'.join([
        'This is a genealogy research exercise. Every record below is synthetic.',
        '',
        'Task:',
        '',
        '```json', json.dumps(task, ensure_ascii=False, indent=2), '```',
        '',
        'Sources:',
        '',
        '```json', json.dumps(sources, ensure_ascii=False, indent=2), '```',
        '',
        'Follow the task instructions. Reply with the JSON result object only, with no Markdown fence and no other text.',
    ])
    files = {'prompt.md': frontmatter({
        'description': f'Benchmark case {case_id}, generated by scripts/build_evals.py.',
        'tags': ['quality', case_id], 'max_turns': 12, 'timeout_seconds': 300, 'allowed_tools': READ_TOOLS,
    }, body)}
    files['graders/bare-json.md'] = frontmatter({'type': 'regex', 'pattern': r'^\s*\{[\s\S]*\}\s*$'})
    files['graders/case-id.md'] = frontmatter({'type': 'regex', 'pattern': r'"case_id"\s*:\s*' + value_pattern(case_id)})
    for a in gold['assertions']:
        field = a['path'].rsplit('/', 1)[1]
        files[f"graders/decision-{field.replace('_', '-')}.md"] = frontmatter({
            'type': 'regex', 'pattern': '"' + rx_escape(field) + r'"\s*:\s*' + value_pattern(a['expected']),
            'weight': 3 if a['critical'] else 1})
    for field in gold['evidence_fields']:
        files[f"graders/evidence-{field.replace('_', '-')}.md"] = frontmatter({
            'type': 'regex', 'pattern': '"' + rx_escape(field) + r'"\s*:\s*\[\s*' + ref + r'(?:\s*,\s*' + ref + r')*\s*\]'})
    files['graders/no-answer-key-access.md'] = frontmatter({
        'type': 'regex', 'target': 'trace', 'pattern': 'answer-keys', 'match': 'not_contains', 'arm': 'both', 'weight': 3})
    return files


def build():
    out = {}
    for name, skill, prompt in TRIGGERS:
        for rel, text in trigger_files(name, skill, prompt).items():
            out[f'trigger-{name}/{rel}'] = text
    for key in sorted((BENCH / 'answer-keys').glob('*.json')):
        gold = json.loads(key.read_text(encoding='utf-8'))
        public = BENCH / 'public' / gold['case_id']
        task = json.loads((public / 'task.json').read_text(encoding='utf-8'))
        sources = json.loads((public / task['source_file']).read_text(encoding='utf-8'))
        for rel, text in quality_files(gold, task, sources).items():
            out[f"quality-{gold['case_id']}/{rel}"] = text
    return out


def on_disk():
    return {str(p.relative_to(EVALS)): p.read_text(encoding='utf-8')
            for p in EVALS.rglob('*') if p.is_file() and 'results' not in p.relative_to(EVALS).parts
            and p.name != 'README.md' and p.name != '.gitignore'}


# Offline grader self-test helpers, used by tests/check_evals.py.

def _set(obj, path, value):
    parts = path[1:].split('/')
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = value


def reference_result(gold):
    """A result built from the answer key. Only a grader self-test; never a performance claim."""
    result = {'case_id': gold['case_id'], 'decisions': {}, 'evidence': {}, 'limitations': ['Synthetic self-test.']}
    for a in gold['assertions']:
        _set(result, a['path'], a['expected'])
    for field in gold['evidence_fields']:
        result['evidence'][field] = list(gold['allowed_source_ids'][:2])
    return result


def _wrong(value):
    if isinstance(value, bool):
        return not value
    if value is None:
        return 'L1'
    if isinstance(value, int):
        return value + 1
    if isinstance(value, list):
        return list(reversed(value)) if len(value) > 1 else []
    return value + ' (wrong)'


def wrong_result(gold):
    result = reference_result(gold)
    for a in gold['assertions']:
        _set(result, a['path'], _wrong(a['expected']))
    for field in gold['evidence_fields']:
        result['evidence'][field] = ['NOT-A-SOURCE']
    return result


def failed_regex_graders(graders, last_message):
    """Names of last_message regex graders that fail on this text (Python re approximates the JS regex)."""
    failed = []
    for name, g in graders.items():
        if g['type'] != 'regex' or g.get('target', 'last_message') != 'last_message':
            continue
        found = re.search(g['pattern'], last_message, re.I if 'i' in g.get('flags', '') else 0) is not None
        if found == (g.get('match', 'contains') == 'not_contains'):
            failed.append(name)
    return sorted(failed)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--check', action='store_true', help='fail if evals/ differs from what this script writes')
    a = p.parse_args()
    want = build()
    if a.check:
        have = on_disk()
        drift = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
        if drift:
            print('evals/ is out of date; run python scripts/build_evals.py')
            for k in drift:
                print('  ' + k)
            return 1
        print(f'evals/ is in sync ({len(want)} files)')
        return 0
    for rel in set(on_disk()) - set(want):
        (EVALS / rel).unlink()
    for rel, text in want.items():
        path = EVALS / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    print(f'wrote {len(want)} files under evals/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
