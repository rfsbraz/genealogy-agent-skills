#!/usr/bin/env python3
"""Install docs offer the skills CLI (npx skills add), which covers agents without a plugin system. No network."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = "npx skills add rfsbraz/genealogy-agent-skills --skill '*'"


class SkillsCli(unittest.TestCase):
    def test_readme_and_install_guide_list_the_skills_cli(self):
        for doc in ('README.md', 'INSTALL.md'):
            with self.subTest(doc=doc):
                self.assertIn(COMMAND, (ROOT / doc).read_text(encoding='utf-8'))

    def test_install_guide_says_to_install_every_skill(self):
        # Specialists link to genealogy-mode's shared files, so a partial install leaves broken links.
        text = (ROOT / 'INSTALL.md').read_text(encoding='utf-8')
        section = text[text.index('### Skills CLI'):]
        section = section[:section.index('\n### ', 1)]
        self.assertRegex(section, r'all 26 skills|every skill')
        self.assertIn('--list', section)

    def test_host_table_links_the_section(self):
        self.assertIn('[Skills CLI](#skills-cli)', (ROOT / 'INSTALL.md').read_text(encoding='utf-8'))
        self.assertTrue(re.search(r'^\| Skills CLI', (ROOT / 'README.md').read_text(encoding='utf-8'), re.M))


if __name__ == '__main__':
    unittest.main(verbosity=2)
