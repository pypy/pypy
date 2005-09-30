import __future__
import autopath
import py
from pypy.interpreter.pycompiler import CPythonCompiler, PythonCompiler, PythonAstCompiler
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.interpreter.argument import Arguments

class BaseTestCompiler:
    def setup_method(self, method):
        self.compiler = self.space.createcompiler()

    def eval_string(self, string, kind='eval'):
        space = self.space
        code = self.compiler.compile(string, '<>', kind, 0)
        return code.exec_code(space, space.newdict([]), space.newdict([]))

    def test_compile(self):
        code = self.compiler.compile('6*7', '<hello>', 'eval', 0)
        assert isinstance(code, PyCode)
        assert code.co_filename == '<hello>'
        space = self.space
        w_res = code.exec_code(space, space.newdict([]), space.newdict([]))
        assert space.int_w(w_res) == 42

    def test_eval_unicode(self):
        assert (eval(unicode('u"\xc3\xa5"', 'utf8')) ==
                unicode('\xc3\xa5', 'utf8'))

    def test_compile_command(self):
        for mode in ('single', 'exec'):
            c0 = self.compiler.compile_command('\t # hello\n ', '?', mode, 0)
            c1 = self.compiler.compile_command('print 6*7', '?', mode, 0)
            c2 = self.compiler.compile_command('if 1:\n  x\n', '?', mode, 0)
            c8 = self.compiler.compile_command('x = 5', '?', mode, 0)
            c9 = self.compiler.compile_command('x = 5 ', '?', mode, 0)
            assert c0 is not None
            assert c1 is not None
            assert c2 is not None
            assert c8 is not None
            assert c9 is not None
            c3 = self.compiler.compile_command('if 1:\n  x', '?', mode, 0)
            c4 = self.compiler.compile_command('x = (', '?', mode, 0)
            c5 = self.compiler.compile_command('x = (\n', '?', mode, 0)
            c6 = self.compiler.compile_command('x = (\n\n', '?', mode, 0)
            c7 = self.compiler.compile_command('x = """a\n', '?', mode, 0)
            assert c3 is None
            assert c4 is None
            assert c5 is None
            assert c6 is None
            assert c7 is None
            space = self.space
            space.raises_w(space.w_SyntaxError, self.compiler.compile_command,
                           'if 1:\n  x x', '?', mode, 0)
            space.raises_w(space.w_SyntaxError, self.compiler.compile_command,
                           ')', '?', mode, 0)

    def test_getcodeflags(self):
        code = self.compiler.compile('from __future__ import division\n',
                                     '<hello>', 'exec', 0)
        flags = self.compiler.getcodeflags(code)
        assert flags & __future__.division.compiler_flag
        # check that we don't get more flags than the compiler can accept back
        code2 = self.compiler.compile('print 6*7', '<hello>', 'exec', flags)
        # check that the flag remains in force
        flags2 = self.compiler.getcodeflags(code2)
        assert flags == flags2

    def test_interactivemode(self):
        code = self.compiler.compile('a = 1', '<hello>', 'single', 0)
        assert isinstance(code, PyCode)
        assert code.co_filename == '<hello>'
        space = self.space
        w_globals = space.newdict([])
        code.exec_code(space, w_globals, w_globals)
        w_a = space.getitem(w_globals, space.wrap('a'))
        assert space.int_w(w_a) == 1

    def test_scope_unoptimized_clash1(self):
        # mostly taken from test_scope.py 
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            def unoptimized_clash1(strip):
                def f(s):
                    from string import *
                    return strip(s) # ambiguity: free or local
                return f""", '', 'exec', 0)
        ex = e.value 
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_scope_unoptimized_clash1_b(self):
        # mostly taken from test_scope.py 
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            def unoptimized_clash1(strip):
                def f():
                    from string import *
                    return s # ambiguity: free or local
                return f""", '', 'exec', 0)
        ex = e.value 
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_scope_exec_in_nested(self):
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            def unoptimized_clash1(x):
                def f():
                    exec "z=3"
                    return x
                return f""", '', 'exec', 0)
        ex = e.value 
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_scope_exec_with_nested_free(self):
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            def unoptimized_clash1(x):
                exec "z=3"
                def f():
                    return x
                return f""", '', 'exec', 0)
        ex = e.value 
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_scope_importstar_in_nested(self):
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            def unoptimized_clash1(x):
                def f():
                    from string import * 
                    return x
                return f""", '', 'exec', 0)
        ex = e.value 
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_scope_importstar_with_nested_free(self):
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            def clash(x):
                from string import *
                def f(s):
                    return strip(s)
                return f""", '', 'exec', 0)
        ex = e.value 
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_toplevel_docstring(self):
        space = self.space
        code = self.compiler.compile('"spam"; "bar"; x=5', '<hello>', 'exec', 0)
        w_locals = space.newdict([])
        code.exec_code(space, space.newdict([]), w_locals)
        w_x = space.getitem(w_locals, space.wrap('x'))
        assert space.eq_w(w_x, space.wrap(5))
        w_doc = space.getitem(w_locals, space.wrap('__doc__'))
        assert space.eq_w(w_doc, space.wrap("spam"))
        #
        code = self.compiler.compile('"spam"; "bar"; x=5',
                                     '<hello>', 'single', 0)
        w_locals = space.newdict([])
        code.exec_code(space, space.newdict([]), w_locals)
        w_x = space.getitem(w_locals, space.wrap('x'))
        assert space.eq_w(w_x, space.wrap(5))
        w_doc = space.call_method(w_locals, 'get', space.wrap('__doc__'))
        assert space.is_w(w_doc, space.w_None)   # "spam" is not a docstring

    def test_barestringstmts_disappear(self):
        space = self.space
        code = self.compiler.compile('"a"\n"b"\n"c"\n', '<hello>', 'exec', 0)
        for w_const in code.co_consts_w:
            # "a" should show up as a docstring, but "b" and "c" should not
            assert not space.eq_w(w_const, space.wrap("b"))
            assert not space.eq_w(w_const, space.wrap("c"))

    def test_unicodeliterals(self):
        e = py.test.raises(OperationError, self.eval_string, "u'\\Ufffffffe'")
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_UnicodeError)

        e = py.test.raises(OperationError, self.eval_string, "u'\\Uffffffff'")
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_UnicodeError)

        e = py.test.raises(OperationError, self.eval_string, "u'\\U%08x'" % 0x110000)
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_UnicodeError)

    def test_argument_handling(self):
        for expr in 'lambda a,a:0', 'lambda a,a=1:0', 'lambda a=1,a=1:0':
            e = py.test.raises(OperationError, self.eval_string, expr)
            ex = e.value
            ex.normalize_exception(self.space)
            assert ex.match(self.space, self.space.w_SyntaxError)

        for code in 'def f(a, a): pass', 'def f(a = 0, a = 1): pass', 'def f(a): global a; a = 1':
            e = py.test.raises(OperationError, self.eval_string, code, 'exec')
            ex = e.value
            ex.normalize_exception(self.space)
            assert ex.match(self.space, self.space.w_SyntaxError)

    def test_argument_order(self):
        code = 'def f(a=1, (b, c)): pass'
        e = py.test.raises(OperationError, self.eval_string, code, 'exec')
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_SyntaxError)
        
    def test_debug_assignment(self):
        code = '__debug__ = 1'
        e = py.test.raises(OperationError, self.compiler.compile, code, '', 'single', 0)
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_return_in_generator(self):
        code = 'def f():\n return None\n yield 19\n'
        e = py.test.raises(OperationError, self.compiler.compile, code, '', 'single', 0)
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_none_assignment(self):
        stmts = [
            'None = 0',
            'None += 0',
            '__builtins__.None = 0',
            'def None(): pass',
            'class None: pass',
            '(a, None) = 0, 0',
            'for None in range(10): pass',
            'def f(None): pass',
        ]
        for stmt in stmts:
            stmt += '\n'
            for kind in 'single', 'exec':
                e = py.test.raises(OperationError, self.compiler.compile, stmt,
                               '', kind, 0)
                ex = e.value
                ex.normalize_exception(self.space)
                assert ex.match(self.space, self.space.w_SyntaxError)

    def test_import(self):
        succeed = [
            'import sys',
            'import os, sys',
            'from __future__ import nested_scopes, generators',
            'from __future__ import (nested_scopes,\ngenerators)',
            'from __future__ import (nested_scopes,\ngenerators,)',
            'from sys import stdin, stderr, stdout',
            'from sys import (stdin, stderr,\nstdout)',
            'from sys import (stdin, stderr,\nstdout,)',
            'from sys import (stdin\n, stderr, stdout)',
            'from sys import (stdin\n, stderr, stdout,)',
            'from sys import stdin as si, stdout as so, stderr as se',
            'from sys import (stdin as si, stdout as so, stderr as se)',
            'from sys import (stdin as si, stdout as so, stderr as se,)',
            ]
        fail = [
            'import (os, sys)',
            'import (os), (sys)',
            'import ((os), (sys))',
            'import (sys',
            'import sys)',
            'import (os,)',
            'from (sys) import stdin',
            'from __future__ import (nested_scopes',
            'from __future__ import nested_scopes)',
            'from __future__ import nested_scopes,\ngenerators',
            'from sys import (stdin',
            'from sys import stdin)',
            'from sys import stdin, stdout,\nstderr',
            'from sys import stdin si',
            'from sys import stdin,'
            'from sys import (*)',
            'from sys import (stdin,, stdout, stderr)',
            'from sys import (stdin, stdout),',
            ]
        for stmt in succeed:
            self.compiler.compile(stmt, 'tmp', 'exec', 0)
        for stmt in fail:
            e = py.test.raises(OperationError, self.compiler.compile,
                               stmt, 'tmp', 'exec', 0)
            ex = e.value
            ex.normalize_exception(self.space)
            assert ex.match(self.space, self.space.w_SyntaxError)

    def test_globals_warnings(self):
        space = self.space
        w_mod = space.appexec((), '():\n import warnings\n return warnings\n') #sys.getmodule('warnings')
        w_filterwarnings = space.getattr(w_mod, space.wrap('filterwarnings'))
        filter_arg = Arguments(space, [ space.wrap('error') ],
                       dict(module=space.wrap('<tmp>')))
                        
        for code in ('''
def wrong1():
    a = 1
    b = 2
    global a
    global b
''', '''
def wrong2():
    print x
    global x
''', '''
def wrong3():
    print x
    x = 2
    global x
'''):

            space.call_args(w_filterwarnings, filter_arg)
            e = py.test.raises(OperationError, self.compiler.compile,
                               code, '<tmp>', 'exec', 0)
            space.call_method(w_mod, 'resetwarnings') 
            ex = e.value
            ex.normalize_exception(space)
            assert ex.match(space, space.w_SyntaxError)
                
class TestECCompiler(BaseTestCompiler):
    def setup_method(self, method):
        self.compiler = self.space.getexecutioncontext().compiler

    def test_globals_warnings(self):
        py.test.skip('INPROGRES')

    def test_return_in_generator(self):
        py.test.skip('INPROGRES')

class TestPyCCompiler(BaseTestCompiler):
    def setup_method(self, method):
        self.compiler = CPythonCompiler(self.space)

class TestPurePythonCompiler(BaseTestCompiler):
    def setup_method(self, method):
        self.compiler = PythonCompiler(self.space)

    def test_globals_warnings(self):
        py.test.skip('INPROGRES')

    def test_return_in_generator(self):
        py.test.skip('INPROGRES')

class TestPythonAstCompiler(BaseTestCompiler):
    def setup_method(self, method):
        self.compiler = PythonAstCompiler(self.space)

class SkippedForNowTestPyPyCompiler(BaseTestCompiler):
    def setup_method(self, method):
        self.compiler = PyPyCompiler(self.space)

