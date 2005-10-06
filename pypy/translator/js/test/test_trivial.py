import py
from pypy.translator.js.test.runtest import compile

def test_CLI():
    def simple1():
        return 42
    f = compile(simple1)
    assert f() == simple1()
