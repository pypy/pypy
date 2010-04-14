
import py
py.test.skip("work in progress")

from pypy.jit.tl.tinyframe import *

class TestCompile(object):
    def test_simple(self):
        code = compile('''
        LOAD 0 => r1
        LOAD 1 => r0 # comment
        # other comment
        ADD r0, r1 => r2
        PRINT r2
        ''')
        assert disassemble(code) == [
            LOAD, 0, 1, LOAD, 1, 0, ADD, 0, 1, 2, PRINT, 2
            ]
