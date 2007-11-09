import py
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rstr import string_repr
from pypy.rpython.test.test_llinterp import interpret 

def test_constant_string():
    def f():
        return "foo"
    res = interpret(f, [], type_system="ootype")
    assert res._str == "foo"

def test_string_builder():
    b = ootype.new(ootype.StringBuilder)
    b.ll_append_char('a')
    b.ll_append(ootype.make_string('bcd'))
    res = b.ll_build()
    assert res._str == 'abcd'

def test_constant_repr():
    myconst = string_repr.convert_const('foo')
    assert isinstance(myconst, ootype._string)

    def f():
        buf = ootype.new(ootype.StringBuilder)
        buf.ll_append(myconst)
        return buf.ll_build()

    res = interpret(f, [], type_system='ootype')
    assert res._str == 'foo'

def test_oounicode():
    u = ootype.oounicode(u'a', -1)
    assert isinstance(u, ootype._string)
    assert ootype.typeOf(u) is ootype.Unicode

    s = ootype.make_string('a string')
    u = ootype.oounicode(s, -1)
    assert isinstance(u, ootype._string)
    assert ootype.typeOf(u) is ootype.Unicode

    s = ootype.make_string('non-ascii string: \xe0')
    py.test.raises(UnicodeDecodeError, ootype.oounicode, s, -1)
    
