#!/usr/bin/env python3
"""The host validator runner and its CI wiring. Uses stub validators; no network."""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts' / 'run_host_validators.py'
INSTALLER = ROOT / 'scripts' / 'install_host_validators.sh'


def stub(path, body):
    path.write_text('#!/usr/bin/env python3\nimport sys\n' + body, encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


class Runner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'package_skills.py'), '--release', '--out', str(cls.dir / 'dist')],
                       check=True, capture_output=True)
        cls.release = cls.dir / 'dist' / 'release'
        # Each stub records its arguments, and fails when the skill folder named in FAIL_ON is passed.
        log = cls.dir / 'calls.log'
        record = f"open({str(log)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        fail = "import os\nsys.exit(1 if os.environ.get('FAIL_ON') and sys.argv[-1].rstrip('/').endswith(os.environ['FAIL_ON']) else 0)\n"
        cls.skills_ref = stub(cls.dir / 'agentskills', record + fail)
        cls.quick = stub(cls.dir / 'quick_validate.py', record + "print('Skill is valid!')\n" + fail)
        cls.claude = stub(cls.dir / 'claude', record + fail)
        cls.log = log

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_runner(self, **env):
        self.log.write_text('', encoding='utf-8')
        return subprocess.run([sys.executable, str(RUNNER), str(self.release), '--skills-ref', str(self.skills_ref),
                               '--quick-validate', str(self.quick), '--claude', str(self.claude), '--python', sys.executable],
                              capture_output=True, text=True, env={**os.environ, **env})

    def test_every_bundle_and_both_plugin_trees_are_validated(self):
        result = self.run_runner()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        skills = len(list((ROOT / 'skills').glob('*/SKILL.md')))
        self.assertEqual(summary['skills-ref'], {'passed': skills, 'failed': []})
        self.assertEqual(summary['quick_validate'], {'passed': skills, 'failed': []})
        self.assertEqual(summary['claude plugin validate'], {'passed': 3, 'failed': []})
        calls = self.log.read_text(encoding='utf-8').splitlines()
        plugin_calls = [c for c in calls if c.startswith('plugin validate')]
        self.assertTrue(all('--strict' in c for c in plugin_calls), plugin_calls)
        # The unpacked zips are validated, not the source folders that still carry disable-model-invocation.
        self.assertFalse([c for c in calls if '/skills/genealogy-' in c and str(ROOT) in c])

    def test_a_failing_validator_fails_the_run_and_names_the_skill(self):
        result = self.run_runner(FAIL_ON='genealogy-reporting')
        self.assertEqual(result.returncode, 1)
        summary = json.loads(result.stdout)
        self.assertEqual(summary['skills-ref']['failed'], ['genealogy-reporting'])
        self.assertEqual(summary['quick_validate']['failed'], ['genealogy-reporting'])


class Wiring(unittest.TestCase):
    def test_installer_pins_every_tool(self):
        text = INSTALLER.read_text(encoding='utf-8')
        for tool, variable in (('skills-ref', 'SKILLS_REF_VERSION'), ('pyyaml', 'PYYAML_VERSION'),
                               ('@anthropic-ai/claude-code', 'CLAUDE_CODE_VERSION')):
            with self.subTest(tool=tool):
                self.assertRegex(text, rf'^{variable}=\d+\.\d+\.\d+$'.replace('^', '(?m)^', 1))
                self.assertIn(f'{tool}' + ('@' if tool.startswith('@') else '==') + f'${{{variable}}}', text)
        self.assertRegex(text, r'(?m)^SKILLS_COMMIT=[0-9a-f]{40}$')
        self.assertIn('anthropics/skills/${SKILLS_COMMIT}/skills/skill-creator/scripts/quick_validate.py', text)
        self.assertRegex(text, r'sha256sum -c')
        self.assertNotIn('latest', text)

    def test_ci_runs_the_validators_on_the_built_assets(self):
        text = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        job = text[text.index('  host-validators:'):]
        for step in ('actions/setup-node', 'scripts/install_host_validators.sh',
                     'python scripts/package_skills.py --release', 'python scripts/run_host_validators.py'):
            with self.subTest(step=step):
                self.assertIn(step, job)

    def test_release_validates_before_upload(self):
        text = (ROOT / '.github/workflows/release-please.yml').read_text(encoding='utf-8')
        self.assertLess(text.index('python scripts/run_host_validators.py'), text.index('gh release upload'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
