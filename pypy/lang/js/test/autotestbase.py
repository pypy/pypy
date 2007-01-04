# encoding: utf-8
"""
autotestbase.py
"""

from pypy.lang.js import interpreter

class TestCase(object):
    code = None
    def setup_class(self):
        self.inter = interpreter.Interpreter(self.code or ";")

    def auto(self, expect, typeof, code):
        self.inter.append_source(code)
        r = self.inter.run()
        assert r.GetValue().ToString() == expect
        # TODO: assert typeof
