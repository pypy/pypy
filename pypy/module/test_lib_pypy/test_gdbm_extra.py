from __future__ import absolute_import
import py
from rpython.tool.udir import udir
try:
    from lib_pypy import gdbm
except ImportError as e:
    py.test.skip(e)

def test_len():
    path = str(udir.join('test_gdbm_extra'))
    g = gdbm.open(path, 'c')
    g['abc'] = 'def'
    assert len(g) == 1
    g['bcd'] = 'efg'
    assert len(g) == 2
    del g['abc']
    assert len(g) == 1

def test_unicode():
    path = unicode(udir.join('test_gdm_unicode'))
    g = gdbm.open(path, 'c')  # does not crash
