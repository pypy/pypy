from pypy.rpython.ootype.ootype import *

def test_simple():
    assert typeOf(1) is Signed
