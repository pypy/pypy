"""
Verify that the PyPy source files have no tabs.
"""

import os
from pypy.conftest import pypydir

ROOT = os.path.abspath(os.path.join(pypydir, '..'))
RPYTHONDIR = os.path.join(ROOT, "rpython")
EXCLUDE = {'/virt_test/lib/python2.7/site-packages/setuptools'}


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

def test_no_pypy_import_in_rpython():
    def walk(reldir):
        print reldir
        if reldir:
            path = os.path.join(RPYTHONDIR, *reldir.split('/'))
        else:
            path = RPYTHONDIR
        if os.path.isfile(path):
            if not path.lower().endswith('.py'):
                return
            with file(path) as f:
                for line in f:
                    if "import" not in line:
                        continue
                    assert "from pypy." not in line
                    assert "import pypy." not in line
        elif os.path.isdir(path) and not os.path.islink(path):
            for entry in os.listdir(path):
                if not entry.startswith('.'):
                    walk('%s/%s' % (reldir, entry))

    walk('')

