#!/usr/bin/env python3
"""Document queue CLI help for file arguments and a clear error for inline JSON.

Deterministic: synthetic records only, no network, no model calls.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/genealogy-document-processing/scripts/document_queue.py'
RECORD = {'document_id': 'DOC1', 'source_id': 'SRC1', 'page_count': 3, 'sha256': 'a' * 64,
          'location': {'kind': 'fixture', 'path': 'example.invalid'}}
COMMANDS = ['init', 'register', 'plan', 'budget', 'claim', 'finish', 'import-run', 'status', 'export', 'restore', 'cancel']


def run(*args, stdin=None, db='q.sqlite', cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), '--db', db, *args], input=stdin,
                          capture_output=True, text=True, cwd=cwd)


def options_without_help(text):
    """Option lines in argparse help that have no description on the same or the next line."""
    lines = text.split('\n')
    start = next(i for i, line in enumerate(lines) if line.startswith('options:') or line.startswith('optional arguments:'))
    missing = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        match = re.match(r'^  (-\S.*?)(?:\s{2,}(\S.*))?$', line)
        if not match:
            continue
        flag, description = match.groups()
        following = lines[i + 1] if i + 1 < len(lines) else ''
        if description is None and not re.match(r'^ {6,}\S', following):
            missing.append(flag.split()[0].rstrip(','))
    return [m for m in missing if m not in ('-h',)]


class Help(unittest.TestCase):
    def test_register_help_describes_record_as_a_json_file_path(self):
        out = subprocess.run([sys.executable, str(SCRIPT), '--db', 'q.sqlite', 'register', '--help'], capture_output=True, text=True).stdout
        self.assertRegex(' '.join(out.split()), r'--record RECORD\s+path to a JSON')

    def test_result_arguments_describe_a_json_file_path(self):
        for command in ('finish', 'import-run'):
            with self.subTest(command=command):
                out = subprocess.run([sys.executable, str(SCRIPT), '--db', 'q.sqlite', command, '--help'], capture_output=True, text=True).stdout
                self.assertRegex(' '.join(out.split()), r'--result RESULT\s+path to a JSON')

    def test_every_option_has_help(self):
        top = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True).stdout
        self.assertEqual(options_without_help(top), [], 'top level')
        for command in COMMANDS:
            with self.subTest(command=command):
                out = subprocess.run([sys.executable, str(SCRIPT), '--db', 'q.sqlite', command, '--help'], capture_output=True, text=True).stdout
                self.assertEqual(options_without_help(out), [])


class JsonFileArguments(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.p = Path(self.temp.name)
        self.assertEqual(run('init', cwd=self.p).returncode, 0)

    def tearDown(self):
        self.temp.cleanup()

    def test_inline_json_gets_a_clear_message(self):
        result = run('register', '--record', json.dumps(RECORD), cwd=self.p)
        self.assertEqual(result.returncode, 2)
        error = json.loads(result.stdout)['error']
        self.assertIn('expected a file path, got inline JSON', error)
        self.assertNotIn('Errno', error)
        self.assertNotIn('DOC1', error)

    def test_missing_file_names_the_argument(self):
        result = run('register', '--record', 'missing.json', cwd=self.p)
        self.assertEqual(result.returncode, 2)
        error = json.loads(result.stdout)['error']
        self.assertIn('--record', error)
        self.assertIn('not found', error)
        self.assertNotIn('Errno', error)

    def test_invalid_json_file_names_the_argument(self):
        (self.p / 'bad.json').write_text('{not json', encoding='utf-8')
        result = run('register', '--record', 'bad.json', cwd=self.p)
        self.assertEqual(result.returncode, 2)
        error = json.loads(result.stdout)['error']
        self.assertIn('--record', error)
        self.assertIn('not valid JSON', error)

    def test_file_path_still_works(self):
        (self.p / 'record.json').write_text(json.dumps(RECORD), encoding='utf-8')
        result = run('register', '--record', 'record.json', cwd=self.p)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)['created'])

    def test_dash_reads_stdin(self):
        result = run('register', '--record', '-', stdin=json.dumps(RECORD), cwd=self.p)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)['created'])


if __name__ == '__main__':
    unittest.main(verbosity=2)


class HostCanonicalDocs(unittest.TestCase):
    def test_host_canonical_covers_artifacts(self):
        cli = (ROOT / 'skills/genealogy-document-processing/references/cli.md').read_text(encoding='utf-8')
        section = cli.split('## Host-canonical mode', 1)[1]
        for phrase in ('Artifacts in host-canonical mode', 'dated run file', 'does not invalidate the reading',
                       'Never update the old hash', 'artifact_git_commit'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)
