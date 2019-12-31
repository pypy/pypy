#!/usr/bin/env python
"""
This is what the buildbot runs to execute the lib-python tests
on top of pypy-c.
"""

import sys, os
import subprocess

rootdir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
os.environ['PYTHONPATH'] = rootdir
os.environ['PYTEST_PLUGINS'] = ''

if sys.platform == 'win32':
    pypyopt = "--pypy=pypy/goal/pypy3-c.exe"
else:
    pypyopt = "--pypy=pypy/goal/pypy3-c"

popen = subprocess.Popen(
    [sys.executable, "pypy/test_all.py",
     pypyopt,
     "--timeout=1324",   # make it easy to search for
     "-rs",
     "--duration=10",
     "--resultlog=cpython.log", "lib-python",
     ] + sys.argv[1:],
    cwd=rootdir)

try:
    ret = popen.wait()
except KeyboardInterrupt:
    popen.kill()
    print "\ninterrupted"
    ret = 1

sys.exit(ret)
