#!/usr/bin/env python3
"""Sanity-check a built site: every local link, image and stylesheet must point at a file that exists.

    python3 tools/check.py dist
"""
import sys, os, re

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'dist')
bad = 0
for d, _, files in os.walk(OUT):
    for f in files:
        if not f.endswith('.html'): continue
        path = os.path.join(d, f)
        text = open(path, encoding='utf-8').read()
        for ref in re.findall(r'(?:href|src)="([^"#]+)"', text):
            if re.match(r'^(https?:|mailto:|tel:|data:)', ref): continue
            target = os.path.normpath(os.path.join(d, ref))
            if os.path.isdir(target): target = os.path.join(target, 'index.html')
            if not os.path.exists(target):
                print(f'{os.path.relpath(path, OUT)}: missing {ref}')
                bad += 1
print('ok' if not bad else f'{bad} broken references')
sys.exit(1 if bad else 0)
