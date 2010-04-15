
import py
from pypy.jit.tl.tinyframe import *

class TestCompile(object):
    def test_simple(self):
        code = compile('''
        main:
        LOAD 0 => r1
        LOAD 1 => r0 # comment
        # other comment
        ADD r0 r1 => r2
        PRINT r2
        ''')
        assert disassemble(code) == [
            LOAD, 0, 1, LOAD, 1, 0, ADD, 0, 1, 2, PRINT, 2
            ]

    def test_return(self):
        code = compile('''
        main:
        LOAD 0 => r1
        LOAD 1 => r0 # comment
        # other comment
        ADD r0 r1 => r2
        RETURN r2
        ''')
        res = interpret(code)
        assert isinstance(res, Int)
        assert res.val == 1

    def test_loop(self):
        code = compile('''
        main:
        LOAD 1 => r1
        LOAD 100 => r2
        LOAD 0 => r0
        @l1
        ADD r0 r1 => r0
        JUMP_IF_ABOVE r2 r0 @l1
        RETURN r0
        ''')
        ret = interpret(code)
        assert ret.val == 100

    def test_function(self):
        code = compile('''
        func: # arg comes in r0
        LOAD 1 => r1
        ADD r0 r1 => r1
        RETURN r1
        main:
        LOAD_FUNCTION func => r0
        LOAD 1 => r1
        CALL r0 r1 => r2
        RETURN r2
        ''')
        ret = interpret(code)
        assert ret.val == 1 + 1
