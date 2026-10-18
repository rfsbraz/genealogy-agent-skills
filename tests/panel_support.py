#!/usr/bin/env python3
"""Shared helpers for the reading panel checks: load the packet helper and fixture renderer, read packets."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACKETS = load('method_packets', 'skills/genealogy-read-manuscripts/scripts/method_packets.py')
PAGES = load('synthetic_pages', 'tests/fixtures/synthetic_pages.py')


def packet_inputs(test, packets, manifest, method):
    """Return (task folder, inputs.json payload) for one method, failing clearly on the old packet layout."""
    packet = manifest['packets'][method]
    test.assertIn('inputs', packet, 'packet has no inputs.json with page-qualified assets')
    path = Path(packets) / packet['inputs']
    return path.parent, json.loads(path.read_text(encoding='utf-8'))


def pin_pages(spec, folder, pages):
    """Register full source pages for packet schema 1.2: {page number: image file in folder}."""
    spec['pages'] = [{'source_id': spec['source_id'], 'page': n, 'image': name,
                      'sha256': hashlib.sha256((Path(folder) / name).read_bytes()).hexdigest(),
                      'source_locator': 'synthetic page %d' % n} for n, name in sorted(pages.items())]
    return spec


def covers(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]
