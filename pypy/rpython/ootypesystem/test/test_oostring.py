from pypy.rpython.test.test_llinterp import interpret 

def test_constant_string():
    def f():
        return "foo"
    res = interpret(f, [], type_system="ootype")
    assert res == "foo"

