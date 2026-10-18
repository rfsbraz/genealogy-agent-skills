#!/usr/bin/env python3
"""Scan tracked files for emails, phone numbers and absolute home paths.

Extra terms come from the PRIVACY_DENYLIST environment variable (one regex per
line, matched case-insensitively). Hits print only file:line, never the text.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_EMAIL_DOMAINS = re.compile(r'@([a-z0-9-]+\.)*(example\.(com|org|net|invalid)|invalid|users\.noreply\.github\.com)$', re.I)
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
BUILTIN = {
    'phone': re.compile(r'(\+\d{2,3}[ .-]?)?\b[29]\d{2}[ .-]?\d{3}[ .-]?\d{3}\b'),
    'home path': re.compile(r'(/(home|Users)/[A-Za-z0-9_.-]+|[A-Za-z]:\\Users\\)'),
}
SKIP_SUFFIXES = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.zip', '.sqlite'}


def tracked():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode().split('\0') if p]


def denylist():
    raw = os.environ.get('PRIVACY_DENYLIST', '')
    return [re.compile(line.strip(), re.I) for line in raw.splitlines() if line.strip()]


def main():
    extra = denylist()
    hits = []
    for rel in tracked():
        path = ROOT / rel
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        if extra and any(p.search(rel) for p in extra):
            hits.append((rel, 0, 'denylist'))
        for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            for email in EMAIL.findall(line):
                if not ALLOWED_EMAIL_DOMAINS.search(email):
                    hits.append((rel, number, 'email'))
            for label, pattern in BUILTIN.items():
                if pattern.search(line):
                    hits.append((rel, number, label))
            if any(p.search(line) for p in extra):
                hits.append((rel, number, 'denylist'))
    for rel, number, label in hits:
        print(f'{rel}:{number}: {label}')
    print(f'{len(hits)} hit(s); denylist terms loaded: {len(extra)}')
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
