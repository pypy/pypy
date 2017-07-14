#!/usr/bin/env python
"""
This is what the buildbot runs to execute the pypyjit tests
on top of pypy-c.
"""

import sys, os
import subprocess

rootdir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
os.environ['PYTHONPATH'] = rootdir
os.environ['PYTEST_PLUGINS'] = ''

popen = subprocess.Popen(
    [sys.executable, "pypy/test_all.py",
     "--pypy=pypy/goal/pypy3-c",
     "--resultlog=pypyjit_new.log",
     "pypy/module/pypyjit/test_pypy_c",
     ] + sys.argv[1:],
    cwd=rootdir)

try:
    ret = popen.wait()
except KeyboardInterrupt:
    popen.kill()
    print "\ninterrupted"
    ret = 1

sys.exit(ret)
