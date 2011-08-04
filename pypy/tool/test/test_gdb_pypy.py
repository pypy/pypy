import py
from pypy.tool import gdb_pypy

class Mock(object):
    def __init__(self, **attrs):
        self.__dict__.update(attrs)

class Field(Mock):
    pass

class Struct(object):
    def __init__(self, fieldnames):
        self._fields = [Field(name=name) for name in fieldnames]

    def fields(self):
        return self._fields[:]

class Value(dict):
    def __init__(self, *args, **kwds):
        dict.__init__(self, *args, **kwds)
        self.type = Struct(self.keys())
        for key, val in self.iteritems():
            if isinstance(val, dict):
                self[key] = Value(val)

def test_mock_objects():
    d = {'a': 1,
         'b': 2,
         'super': {
            'c': 3,
            }
         }
    val = Value(d)
    assert val['a'] == 1
    assert val['b'] == 2
    assert isinstance(val['super'], Value)
    assert val['super']['c'] == 3
    fields = val.type.fields()
    names = [f.name for f in fields]
    assert sorted(names) == ['a', 'b', 'super']

def test_find_field_with_suffix():
    obj = Value(x_foo = 1,
                y_bar = 2,
                z_foobar = 3)
    assert gdb_pypy.find_field_with_suffix(obj, 'foo') == 1
    assert gdb_pypy.find_field_with_suffix(obj, 'foobar') == 3
    py.test.raises(KeyError, "gdb_pypy.find_field_with_suffix(obj, 'bar')")
    py.test.raises(KeyError, "gdb_pypy.find_field_with_suffix(obj, 'xxx')")

def test_lookup():
    d = {'r_super': {
            '_gcheader': {
                'h_tid': 123,
                }
            },
         'r_foo': 42,
         }
    obj = Value(d)
    assert gdb_pypy.lookup(obj, 'foo') == 42
    hdr = gdb_pypy.lookup(obj, 'gcheader')
    assert hdr['h_tid'] == 123
