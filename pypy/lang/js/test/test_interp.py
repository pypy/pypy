
from pypy.lang.js.astgen import *
from pypy.lang.js import interpreter
from pypy.lang.js.parser import parse

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

class TestInterp(object):
    def assert_prints(self, code, assval):
        s = StringIO()
        oldstdout = sys.stdout
        sys.stdout = s
        code.call()
        assert s.getvalue() == assval
        sys.stdout = oldstdout
    
    def test_interp_parse(self):
        self.assert_prints(from_dict(parse("print(1+1)")), "2\n")
        self.assert_prints(from_dict(parse("print(1+2+3); print(1)")), "6\n1\n")
        self.assert_prints(from_dict(parse("print(1,2,3);\n")), "1,2,3\n")

