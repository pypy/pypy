from pypy.rpython.ootypesystem import ootype
from pypy.rpython.test.test_llinterp import interpret 

def test_constant_string():
    def f():
        return "foo"
    res = interpret(f, [], type_system="ootype")
    assert res._str == "foo"

def test_builtin_method():
    s = ootype.make_string('foo bar')
    assert s.ll_startswith('foo') == True
    assert s.ll_upper()._str == 'FOO BAR'

def test_split():
    s = ootype.make_string('foo bar')
    res = s.ll_split()
    assert isinstance(res, ootype._list)
    assert res.ll_getitem_fast(0)._str == 'foo'
    assert res.ll_getitem_fast(1)._str == 'bar'
