
from pypy.lang.js.astgen import *
from pypy.lang.js import interpreter

def test_simple():
    assert Plus(Number(3), Number(4)).call() == 7
#    s = Script([Semicolon(Plus(Number(3), Number(4)))], [], [])
#    s.call()
