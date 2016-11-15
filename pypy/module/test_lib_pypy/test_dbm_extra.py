from __future__ import absolute_import
import py
from rpython.tool.udir import udir
try:
    from lib_pypy import dbm
except ImportError as e:
    py.test.skip(e)

import sys
if '__pypy__' not in sys.builtin_module_names:
    skip("lib_pypy.dbm requires PyPy's ctypes")

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

def test_extra():
    py.test.raises(TypeError, dbm.datum, 123)
    py.test.raises(TypeError, dbm.datum, False)

def test_null():
    db = dbm.open('test', 'c')
    db['1'] = 'a\x00b'
    db.close()

    db = dbm.open('test', 'r')
    assert db['1'] == 'a\x00b'
    db.close()

def test_key_with_empty_value():
    # this test fails on CPython too (at least on tannit), and the
    # case shows up when gdbm is not installed and test_anydbm.py
    # falls back dbm.
    py.test.skip("test may fail on CPython too")
    path = str(udir.join('test_dbm_extra.test_key_with_empty_value'))
    d = dbm.open(path, 'c')
    assert 'key_with_empty_value' not in d
    d['key_with_empty_value'] = ''
    assert 'key_with_empty_value' in d
    assert d['key_with_empty_value'] == ''
    d.close()
