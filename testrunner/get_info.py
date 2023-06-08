#!/usr/bin/env python
"""
Dump some translation information to stdout as JSON. Used by buildbot.
"""

import sys
import os
import json

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if sys.platform.startswith('win'):
    TARGET_NAME = 'pypy-c.exe'
    VENV_TARGET = 'pypy.exe'
    TARGET_DIR = 'Scripts'
else:
    TARGET_NAME = 'pypy-c'
    VENV_TARGET = 'pypy'
    TARGET_DIR = 'bin'
VENV_DIR = 'pypy-venv'

def make_info_dict():
    target_path = os.path.join(BASE_DIR, 'pypy', 'goal', TARGET_NAME)
    return {'target_path': target_path,
            'virt_pypy': os.path.join(VENV_DIR, TARGET_DIR, VENV_TARGET),
            'venv_dir': VENV_DIR,
            'project': 'PyPy', # for benchmarks
           }

def dump_info():
    return json.dumps(make_info_dict())

if __name__ == '__main__':
    print dump_info()
