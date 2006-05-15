from pypy.rpython.ootypesystem import ootype
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
