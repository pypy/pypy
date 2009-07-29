import py
from pypy.lib import dbm
from pypy.tool.udir import udir

def test_get():
    path = str(udir.join('test_dbm_extra.test_get'))
    d = dbm.open(path, 'c')
    x = d.get("42")
    assert x is None
    d.close()

def test_set_nonstring():
    path = str(udir.join('test_dbm_extra.test_set_nonstring'))
    d = dbm.open(path, 'c')
    py.test.raises(TypeError, "d[123] = 'xyz'")
    py.test.raises(TypeError, "d['xyz'] = 123")
    d.close()
