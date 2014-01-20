#!/usr/bin/env python2.7

import os, os.path, sys

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

try:
    import pip
except ImportError:
    raise ImportError("Please install pip")

# list of (package_name, import_name)
REQUIRED = [ ("sh", "sh") ]
for (pkg, mod) in REQUIRED:
    try:
        exec("import %s" % mod)
    except ImportError:
        print("Installing %s..." % pkg)
        pip.main(['install', '--user', pkg])
        exec("import %s" % mod) # should pass this time

if sys.platform.startswith("openbsd"):
    cc = "egcc" # bugs in base compiler. uses loads of memory
else:
    cc = "gcc"

env = os.environ.copy()
env["CC"] = cc

os.chdir(os.path.join(SCRIPT_DIR, "pypy", "goal"))
sh.Command(sys.executable)(
    "../../rpython/bin/rpython", "-Ojit", "targetpypystandalone.py",
    _env=env, _out=sys.stdout, _err=sys.stderr)
