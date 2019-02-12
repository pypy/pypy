#!/usr/bin/env python
"""
Dump some translation information to stdout as JSON. Used by buildbot.
"""

import sys
import os
import json

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if sys.platform.startswith('win'):
    TARGET_NAME = r'pypy-c.exe'
    # see https://github.com/pypa/virtualenv/issues/789
    TARGET_DIR = 'bin'
else:
    TARGET_NAME = 'pypy-c'
    TARGET_DIR = 'bin'
VENV_DIR = 'pypy-venv'

def make_info_dict():
    target_path = os.path.join(BASE_DIR, 'pypy', 'goal', TARGET_NAME)
    return {'target_path': target_path,
            'virt_pypy': os.path.join(VENV_DIR, TARGET_DIR, TARGET_NAME),
            'venv_dir': VENV_DIR,
           }

def dump_info():
    return json.dumps(make_info_dict())

if __name__ == '__main__':
    print dump_info()
