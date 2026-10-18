#!/usr/bin/env python3
"""Repository discovery accepts host-documented endpoints with provenance, still forbids
guessed endpoints, and records truncated search results as partial coverage. Text checks only."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/genealogy-repository-discovery'


def text(rel):
    return re.sub(r'\s+', ' ', (SKILL / rel).read_text(encoding='utf-8'))


def step(number):
    match = re.search(r'(?m)^%d\. (.+)$' % number, (SKILL / 'SKILL.md').read_text(encoding='utf-8'))
    return match.group(1) if match else ''


class DocumentedRoutes(unittest.TestCase):
    def test_step_6_accepts_host_documented_endpoints_with_provenance(self):
        access = step(6)
        self.assertIn('documented by the host project', access)
        for needed in ('provenance', 'checked', 'route_provenance'):
            self.assertIn(needed, access)

    def test_step_6_still_forbids_guessed_endpoints_and_id_manipulation(self):
        access = step(6)
        self.assertIn('never invent API endpoints', access)
        self.assertIn('manipulate IDs', access)

    def test_portugal_reference_defers_to_documented_route_rule(self):
        portugal = text('references/portugal.md')
        self.assertIn('asserts no public API', portugal)
        self.assertIn('documented by the host project', portugal)
        self.assertIn('step 6', portugal)


class ProfileTemplate(unittest.TestCase):
    def test_template_records_route_provenance(self):
        template = json.loads((SKILL / 'assets/repository-profile-template.json').read_text(encoding='utf-8'))
        self.assertIn('route_provenance', template)
        entry = template['route_provenance'][0]
        for key in ('route', 'found_via', 'documented_by', 'observed_from', 'checked_on', 'scope'):
            self.assertIn(key, entry)
        self.assertIn('host_project_document', entry['found_via'])
        self.assertIn('official_link', entry['found_via'])

    def test_protocol_schema_lists_route_provenance(self):
        self.assertIn('route_provenance', text('references/discovery-protocol.md'))


class TruncatedSearches(unittest.TestCase):
    def test_protocol_records_capped_result_lists_as_partial(self):
        protocol = text('references/discovery-protocol.md')
        self.assertRegex(protocol, r'truncated|capped')
        self.assertIn('record the cap', protocol)
        self.assertIn('partial', protocol)
        self.assertIn('never complete', protocol)


if __name__ == '__main__':
    unittest.main(verbosity=2)
