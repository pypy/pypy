# encoding: utf-8
import pytest
import py, sys
from pypy.interpreter.pycompiler import PythonAstCompiler
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.interpreter.argument import Arguments
from pypy.tool import stdlib___future__ as __future__

class TestPythonAstCompiler:
    def setup_method(self, method):
        self.compiler = self.space.createcompiler()

    def eval_string(self, string, kind='eval'):
        space = self.space
        code = self.compiler.compile(string, '<>', kind, 0)
        return code.exec_code(space, space.newdict(), space.newdict())

    def test_compile(self):
        code = self.compiler.compile('6*7', '<hello>', 'eval', 0)
        assert isinstance(code, PyCode)
        assert code.co_filename == '<hello>'
        space = self.space
        w_res = code.exec_code(space, space.newdict(), space.newdict())
        assert space.int_w(w_res) == 42

    def test_eval_unicode(self):
        assert (eval(unicode('u"\xc3\xa5"', 'utf8')) ==
                unicode('\xc3\xa5', 'utf8'))

    def test_compile_command(self):
        for mode in ('single', 'exec'):
            c0 = self.compiler.compile_command('\t # hello\n ', '?', mode, 0)
            c1 = self.compiler.compile_command('print(6*7)', '?', mode, 0)
            c2 = self.compiler.compile_command('if 1:\n  x\n', '?', mode, 0)
            c8 = self.compiler.compile_command('x = 5', '?', mode, 0)
            c9 = self.compiler.compile_command('x = 5 ', '?', mode, 0)
            assert c0 is not None
            assert c1 is not None
            assert c2 is not None
            assert c8 is not None
            assert c9 is not None
            c4 = self.compiler.compile_command('x = (', '?', mode, 0)
            c5 = self.compiler.compile_command('x = (\n', '?', mode, 0)
            c6 = self.compiler.compile_command('x = (\n\n', '?', mode, 0)
            c7 = self.compiler.compile_command('x = """a\n', '?', mode, 0)
            assert c4 is None
            assert c5 is None
            assert c6 is None
            assert c7 is None
            space = self.space
            space.raises_w(space.w_SyntaxError, self.compiler.compile_command,
                           'if 1:\n  x x', '?', mode, 0)
            space.raises_w(space.w_SyntaxError, self.compiler.compile_command,
                           ')', '?', mode, 0)
        c3 = self.compiler.compile_command('if 1:\n  x', '?', 'single', 0)
        assert c3 is None

    def test_compile_bug(self):
        self.compiler.compile_command("if 1: pass", "", "single", 0)

    def test_hidden_applevel(self):
        code = self.compiler.compile("def f(x): pass", "<test>", "exec", 0,
                                     True)
        assert code.hidden_applevel
        for w_const in code.co_consts_w:
            if isinstance(w_const, PyCode):
                assert code.hidden_applevel

    def test_indentation_error(self):
        space = self.space
        space.raises_w(space.w_SyntaxError, self.compiler.compile_command,
                       'if 1:\n  x\n y\n', '?', 'exec', 0)

    def test_getcodeflags(self):
        code = self.compiler.compile('from __future__ import division, annotations\n',
                                     '<hello>', 'exec', 0)
        flags = self.compiler.getcodeflags(code)
        assert flags & __future__.division.compiler_flag == 0
        assert flags & __future__.annotations.compiler_flag
        # check that we don't get more flags than the compiler can accept back
        code2 = self.compiler.compile('print(6*7)', '<hello>', 'exec', flags)
        # check that the flag remains in force
        flags2 = self.compiler.getcodeflags(code2)
        assert flags == flags2

    def test_interactivemode(self):
        code = self.compiler.compile('a = 1', '<hello>', 'single', 0)
        assert isinstance(code, PyCode)
        assert code.co_filename == '<hello>'
        space = self.space
        w_globals = space.newdict()
        code.exec_code(space, w_globals, w_globals)
        w_a = space.getitem(w_globals, space.wrap('a'))
        assert space.int_w(w_a) == 1

    def test_signature_kwargname(self):
        from pypy.interpreter.pycode import make_signature
        from pypy.interpreter.signature import Signature

        def find_func(code):
            for w_const in code.co_consts_w:
                if isinstance(w_const, PyCode):
                    return w_const

        snippet = 'def f(a, b, m=1, n=2, **kwargs):\n pass\n'
        containing_co = self.compiler.compile(snippet, '<string>', 'single', 0)
        co = find_func(containing_co)
        sig = make_signature(co)
        assert sig == Signature(['a', 'b', 'm', 'n'], None, 'kwargs')

        snippet = 'def f(a, b, *, m=1, n=2, **kwargs):\n pass\n'
        containing_co = self.compiler.compile(snippet, '<string>', 'single', 0)
        co = find_func(containing_co)
        sig = make_signature(co)
        assert sig == Signature(['a', 'b', 'm', 'n'], None, 'kwargs', 2)

        # a variant with varargname, which was buggy before issue2996
        snippet = 'def f(*args, offset=42):\n pass\n'
        containing_co = self.compiler.compile(snippet, '<string>', 'single', 0)
        co = find_func(containing_co)
        sig = make_signature(co)
        assert sig == Signature(['offset'], 'args', None, 1)

