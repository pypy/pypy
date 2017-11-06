#!/usr/bin/env python
"""
Dump some translation information to stdout as JSON. Used by buildbot.
"""

import sys
import os
import json

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
TARGET_BASENAME = 'pypy-c'

def make_info_dict():
    target = TARGET_BASENAME
    if sys.platform.startswith('win'):
        target += '.exe'
    target_path = os.path.join(BASE_DIR, 'pypy', 'goal', target)
    return {'target_path': target_path}

def dump_info():
    return json.dumps(make_info_dict())

if __name__ == '__main__':
    print dump_info()
