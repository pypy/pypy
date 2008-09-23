"""
Verify that the PyPy source files have no tabs.
"""

import autopath
import os

ROOT = autopath.pypydir
EXCLUDE = {}


def test_no_tabs():
    def walk(reldir):
        if reldir in EXCLUDE:
            return
        if reldir:
            path = os.path.join(ROOT, *reldir.split('/'))
        else:
            path = ROOT
        if os.path.isfile(path):
            if path.lower().endswith('.py'):
                f = open(path, 'r')
                data = f.read()
                f.close()
                assert '\t' not in data, "%r contains tabs!" % (reldir,)
        elif os.path.isdir(path) and not os.path.islink(path):
            for entry in os.listdir(path):
                if not entry.startswith('.'):
                    walk('%s/%s' % (reldir, entry))
    walk('')
