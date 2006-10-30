
from pypy.lang.js.astgen import *
from pypy.lang.js import interpreter

import sys
from StringIO import StringIO

def test_simple():
    assert Plus(Number(3), Number(4)).call() == 7
#    s = Script([Semicolon(Plus(Number(3), Number(4)))], [], [])
#    s.call()
    s = StringIO()
    oldstdout = sys.stdout
    sys.stdout = s

    Script([Semicolon(Call(Identifier('print'), List([Number(1), Number(2)])))],[],[]).call()
    assert s.getvalue() == '1,2\n'
    sys.stdout = oldstdout
