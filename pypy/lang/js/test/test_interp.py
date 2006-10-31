
from pypy.lang.js.astgen import *
from pypy.lang.js import interpreter
from pypy.lang.js.parser import parse

import sys
from StringIO import StringIO

def parse_d(code):
    return from_dict(parse(code))

class TestInterp(object):
    def test_simple(self):
        assert Plus(Number(3), Number(4)).call().floatval == 7
        #    s = Script([Semicolon(Plus(Number(3), Number(4)))], [], [])
        #    s.call()
        l = []
        interpreter.writer = l.append
        Script([Semicolon(Call(Identifier('print'), List([Number(1), Number(2)])))],[],[]).call()
        assert l == ['1,2']

    def assert_prints(self, code, assval):
        l = []
        interpreter.writer = l.append
        code.call()
        assert l == assval
    
    def test_interp_parse(self):
        self.assert_prints(parse_d("print(1+1)"), ["2"])
        self.assert_prints(parse_d("print(1+2+3); print(1)"), ["6", "1"])
        self.assert_prints(parse_d("print(1,2,3);\n"), ["1,2,3"])

    def test_var_assign(self):
        self.assert_prints(parse_d("x=3;print(x);"), ["3"])
        self.assert_prints(parse_d("x=3;y=4;print(x+y);"), ["7"])

    def test_string_var(self):
        self.assert_prints(parse_d("print(\"sss\");"), ["sss"])
    
    def test_string_concat(self):
        self.assert_prints(parse_d('x="xxx"; y="yyy"; print(x+y);'), ["xxxyyy"])
    
    def test_string_num_concat(self):
        self.assert_prints(parse_d('x=4; y="x"; print(x+y, y+x);'), ["4x,x4"])

    def test_to_string(self):
        self.assert_prints(parse_d("x={}; print(x);"), ["[object Object]"])
