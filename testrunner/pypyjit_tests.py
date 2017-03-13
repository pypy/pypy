#!/usr/bin/env python
"""
This is what the buildbot runs to execute the pypyjit tests
on top of pypy-c.
"""

import sys, os
import subprocess

rootdir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))

popen = subprocess.Popen(
    ["pypy/goal/pypy-c", "pypy/test_all.py",
                         "--resultlog=pypyjit_new.log",
                         "pypy/module/pypyjit/test_pypy_c"],
    cwd=rootdir)

try:
    ret = popen.wait()
except KeyboardInterrupt:
    popen.kill()
    print "\ninterrupted"
    ret = 1

sys.exit(ret)
