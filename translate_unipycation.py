#!/usr/bin/env python2.7

import os, os.path, sys

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

if sys.platform.startswith("openbsd"):
    cc = "egcc" # bugs in base compiler. uses loads of memory
else:
    cc = "gcc"

env = os.environ.copy()
env["CC"] = cc
env["PYTHONPATH"] = os.path.join(SCRIPT_DIR, "deps", "pyrolog")

os.chdir(os.path.join(SCRIPT_DIR, "pypy", "goal"))

os.execve("../../rpython/bin/rpython", [
    "../../rpython/bin/rpython", "-Ojit", "targetpypystandalone.py"],
    env)
