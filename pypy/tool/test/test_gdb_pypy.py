import py
from pypy.tool import gdb_pypy

class FakeGdb(object):

    COMMAND_NONE = -1
    #
    TYPE_CODE_PTR = 1
    TYPE_CODE_ARRAY = 2
    TYPE_CODE_STRUCT = 3

    def __init__(self, exprs, progspace=None):
        self.exprs = exprs
        self.progspace = progspace

    def parse_and_eval(self, expr):
        return self.exprs[expr]

    def current_progspace(self):
        return self.progspace


class Mock(object):
    def __init__(self, **attrs):
        self.__dict__.update(attrs)

class Field(Mock):
    pass

class Struct(object):
    code = FakeGdb.TYPE_CODE_STRUCT
    
    def __init__(self, fieldnames, tag):
        self._fields = [Field(name=name) for name in fieldnames]
        self.tag = tag

    def fields(self):
        return self._fields[:]

class Pointer(object):
    code = FakeGdb.TYPE_CODE_PTR

    def __init__(self, target):
        self._target = target

    def target(self):
        return self._target

class Value(dict):
    def __init__(self, *args, **kwds):
        type_tag = kwds.pop('type_tag', None)
        dict.__init__(self, *args, **kwds)
        self.type = Struct(self.keys(), type_tag)
        for key, val in self.iteritems():
            if isinstance(val, dict):
                self[key] = Value(val)

class PtrValue(Value):
    def __init__(self, *args, **kwds):
        # in python gdb, we can use [] to access fields either if we have an
        # actual struct or a pointer to it, so we just reuse Value here
        Value.__init__(self, *args, **kwds)
        self.type = Pointer(self.type)

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

def test_load_typeids(tmpdir):
    exe = tmpdir.join('testing_1').join('pypy-c')
    typeids = tmpdir.join('typeids.txt')
    typeids.write("""
member0    GcStruct xxx {}
""".strip())
    progspace = Mock(filename=str(exe))
    exprs = {
        '((char*)(&pypy_g_typeinfo.member0)) - (char*)&pypy_g_typeinfo': 0,
        }
    gdb = FakeGdb(exprs, progspace)
    cmd = gdb_pypy.RPyType(gdb)
    typeids = cmd.load_typeids(progspace)
    assert typeids[0] == 'GcStruct xxx {}'

def test_RPyType(tmpdir):
    exe = tmpdir.join('pypy-c')
    typeids = tmpdir.join('typeids.txt')
    typeids.write("""
member0    GcStruct xxx {}
member1    GcStruct yyy {}
member2    GcStruct zzz {}
""".strip())
    #
    progspace = Mock(filename=str(exe))
    d = {'r_super': {
            '_gcheader': {
                'h_tid': 123,
                }
            },
         'r_foo': 42,
         }
    myvar = Value(d)
    exprs = {
        '*myvar': myvar,
        '((char*)(&pypy_g_typeinfo.member0)) - (char*)&pypy_g_typeinfo': 0,
        '((char*)(&pypy_g_typeinfo.member1)) - (char*)&pypy_g_typeinfo': 123,
        '((char*)(&pypy_g_typeinfo.member2)) - (char*)&pypy_g_typeinfo': 456,
        }
    gdb = FakeGdb(exprs, progspace)
    cmd = gdb_pypy.RPyType(gdb)
    assert cmd.do_invoke('*myvar', True) == 'GcStruct yyy {}'

def test_pprint_string():
    d = {'_gcheader': {
            'h_tid': 123
            },
         'rs_hash': 456,
         'rs_chars': {
            'length': 6,
            'items': map(ord, 'foobar'),
            }
         }
    p_string = PtrValue(d, type_tag='pypy_rpy_string0')
    printer = gdb_pypy.RPyStringPrinter.lookup(p_string, FakeGdb)
    assert printer.to_string() == "r'foobar'"

def test_pprint_list():
    d = {'_gcheader': {
            'h_tid': 123
            },
         'l_length': 3, # the lenght of the rpython list
         'l_items':
             # this is the array which contains the items
             {'_gcheader': {
                'h_tid': 456
                },
              'length': 5, # the lenght of the underlying array
              'items': [40, 41, 42, -1, -2],
              }
         }
    mylist = PtrValue(d, type_tag='pypy_list0')
    printer = gdb_pypy.RPyListPrinter.lookup(mylist, FakeGdb)
    assert printer.to_string() == 'r[40, 41, 42] (len=3, alloc=5)'
    #
    mylist.type.target().tag = 'pypy_list1234'
    printer = gdb_pypy.RPyListPrinter.lookup(mylist, FakeGdb)
    assert printer.to_string() == 'r[40, 41, 42] (len=3, alloc=5)'
