import py
from pypy.lib import dbm
from pypy.tool.udir import udir

def test_get():
    path = str(udir.join('test_dbm_extra.test_get'))
    d = dbm.open(path, 'c')
    x = d.get("42")
    assert x is None
    d.close()

def test_delitem():
    path = str(udir.join('test_dbm_extra.test_delitem'))
    d = dbm.open(path, 'c')
    py.test.raises(KeyError, "del d['xyz']")

def test_nonstring():
    path = str(udir.join('test_dbm_extra.test_nonstring'))
    d = dbm.open(path, 'c')
    py.test.raises(TypeError, "d[123] = 'xyz'")
    py.test.raises(TypeError, "d['xyz'] = 123")
    py.test.raises(TypeError, "d['xyz'] = None")
    py.test.raises(TypeError, "del d[123]")
    py.test.raises(TypeError, "d[123]")
    py.test.raises(TypeError, "123 in d")
    py.test.raises(TypeError, "d.has_key(123)")
    py.test.raises(TypeError, "d.setdefault(123, 'xyz')")
    py.test.raises(TypeError, "d.setdefault('xyz', 123)")
    py.test.raises(TypeError, "d.get(123)")
    assert dict(d) == {}
    d.setdefault('xyz', '123')
    assert dict(d) == {'xyz': '123'}
    d.close()

def test_multiple_sets():
    path = str(udir.join('test_dbm_extra.test_multiple_sets'))
    d = dbm.open(path, 'c')
    d['xyz'] = '12'
    d['xyz'] = '3'
    d['xyz'] = '546'
    assert dict(d) == {'xyz': '546'}
    assert d['xyz'] == '546'
