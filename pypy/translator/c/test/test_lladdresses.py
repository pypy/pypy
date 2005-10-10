from pypy.rpython.memory import lladdress
from pypy.translator.c.test.test_genc import compile

def test_null():
    def f():
        return lladdress.NULL - lladdress.NULL
    fc = compile(f, [])
