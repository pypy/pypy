# encoding: utf-8
"""
autotestbase.py
"""

from pypy.lang.js import interpreter
from pypy.lang.js.interpreter import *
from pypy.lang.js.test.conftest import option
import py

if not option.ecma:
    py.test.skip('skipping ecma tests, use --ecma to run then')
    print hello
    
class TestCase(object):
    def setup_class(self):
        self.inter = interpreter.Interpreter()
        if base() is not None:
            self.inter.run(load_source(base()))
            
    def base(self):
        return None

    def auto(self, expect, typeof, code):
        r = self.inter.run(load_source(code))
        assert r.GetValue().ToString() == expect
        # TODO: assert typeof
