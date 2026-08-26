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
        # as far as I can tell, this case can be handled correctly
        # by the interpreter so a SyntaxError is not required, but
        # let's give one anyway for "compatibility"...

        # mostly taken from test_scope.py
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            def unoptimized_clash1(strip):
                def f():
                    from string import *
                    return s # ambiguity: free or local (? no, global or local)
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

    def test_try_except_finally(self):
        s = py.code.Source("""
        def f():
            try:
               1/0
            except ZeroDivisionError:
               pass
            finally:
               return 3
        """)
        self.compiler.compile(str(s), '', 'exec', 0)
        s = py.code.Source("""
        def f():
            try:
                1/0
            except:
                pass
            else:
                pass
            finally:
                return 2
        """)
        self.compiler.compile(str(s), '', 'exec', 0)

    def test_toplevel_docstring(self):
        space = self.space
        code = self.compiler.compile('"spam"; "bar"; x=5', '<hello>', 'exec', 0)
        w_locals = space.newdict()
        code.exec_code(space, space.newdict(), w_locals)
        w_x = space.getitem(w_locals, space.wrap('x'))
        assert space.eq_w(w_x, space.wrap(5))
        w_doc = space.getitem(w_locals, space.wrap('__doc__'))
        assert space.eq_w(w_doc, space.wrap("spam"))
        #
        code = self.compiler.compile('"spam"; "bar"; x=5',
                                     '<hello>', 'single', 0)
        w_locals = space.newdict()
        code.exec_code(space, space.newdict(), w_locals)
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
        assert ex.match(self.space, self.space.w_SyntaxError)

        e = py.test.raises(OperationError, self.eval_string, "u'\\Uffffffff'")
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_SyntaxError)

        e = py.test.raises(OperationError, self.eval_string, "u'\\U%08x'" % 0x110000)
        ex = e.value
        ex.normalize_exception(self.space)
        assert ex.match(self.space, self.space.w_SyntaxError)

    def test_unicode_docstring(self):
        space = self.space
        code = self.compiler.compile('"hello"\n', '<hello>', 'exec', 0)
        assert space.eq_w(code.co_consts_w[0], space.wrap("hello"))
        assert space.is_w(space.type(code.co_consts_w[0]), space.w_unicode)

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
        self.compiler.compile(code, '', 'single', 0)

    def test_yield_in_finally(self):
        code ='def f():\n try:\n  yield 19\n finally:\n  pass\n'
        self.compiler.compile(code, '', 'single', 0)

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
            'from __future__ import (\nnested_scopes,\ngenerators)',
            'from __future__ import(\n\tnested_scopes,\n\tgenerators)',
            'from __future__ import(\n\t\nnested_scopes)',
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

    def test_future_error_offset(self):
        space = self.space
        with pytest.raises(OperationError) as excinfo:
            self.compiler.compile("from __future__ import bogus", "tmp", "exec", 0)
        ex = excinfo.value
        assert ex.match(space, space.w_SyntaxError)
        ex.normalize_exception(space)
        w_exc = ex.get_w_value(space)
        assert space.int_w(w_exc.w_offset) == 24

    def test_globals_warnings(self):
        space = self.space
        w_mod = space.appexec((), '():\n import warnings\n return warnings\n') #sys.getmodule('warnings')
        w_filterwarnings = space.getattr(w_mod, space.wrap('filterwarnings'))
        filter_arg = Arguments(space, [ space.wrap('error') ], [space.newtext("module")],
                               [space.wrap("<tmp>")])

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

    def test_no_warning_run(self):
        space = self.space
        w_mod = space.appexec((), '():\n import warnings\n return warnings\n') #sys.getmodule('warnings')
        w_filterwarnings = space.getattr(w_mod, space.wrap('filterwarnings'))
        filter_arg = Arguments(space, [ space.wrap('error') ], [space.newtext("module")],
                               [space.wrap("<tmp>")])
        for code in ['''
def testing():
    __class__ = 0
    def f():
        nonlocal __class__
        __class__ = 42
    f()
    return __class__
''', '''
class Y:
    class X:
        nonlocal __class__
        __class__ = 42
    assert locals()['__class__'] == 42
    # ^^^ but at the same place, reading '__class__' gives a NameError
    # in CPython 3.5.2.  Looks like a bug to me
def testing():
    return 42
''', '''
class Y:
    def f():
        __class__
    __class__ = 42
def testing():
    return Y.__dict__['__class__']
''', '''
class X:
    foobar = 42
    def f(self):
        return __class__.__dict__['foobar']
def testing():
    return X().f()
''',
#--------XXX the following case is not implemented for now
#'''
#class X:
#    foobar = 42
#    def f(self):
#        class Y:
#            Xcls = __class__
#        return Y.Xcls.__dict__['foobar']
#def testing():
#    return X().f()
#'''
        ]:
            space.call_args(w_filterwarnings, filter_arg)
            pycode = self.compiler.compile(code, '<tmp>', 'exec', 0)
            space.call_method(w_mod, 'resetwarnings')
            w_d = space.newdict()
            pycode.exec_code(space, w_d, w_d)
            w_res = space.call_function(
                space.getitem(w_d, space.wrap('testing')))
            assert space.unwrap(w_res) == 42

    def test_firstlineno(self):
        snippet = str(py.code.Source(r'''
            def f(): "line 2"
            if 3 and \
               (4 and
                  5):
                def g(): "line 6"
            fline = f.__code__.co_firstlineno
            gline = g.__code__.co_firstlineno
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        code.exec_code(space, w_d, w_d)
        w_fline = space.getitem(w_d, space.wrap('fline'))
        w_gline = space.getitem(w_d, space.wrap('gline'))
        assert space.int_w(w_fline) == 2
        assert space.int_w(w_gline) == 6

    def test_firstlineno_decorators(self):
        snippet = str(py.code.Source(r'''
            def foo(x): return x
            @foo       # line 3
            @foo       # line 4
            def f():   # line 5
                pass   # line 6
            fline = f.__code__.co_firstlineno
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        code.exec_code(space, w_d, w_d)
        w_fline = space.getitem(w_d, space.wrap('fline'))
        assert space.int_w(w_fline) == 3

    def test_firstlineno_decorators_class(self):
        snippet = str(py.code.Source(r'''
            def foo(x): return x
            def f():
                @foo       # line 4
                @foo       # line 5
                class AWrong:
                    pass   # line 7
            Aline = f.__code__.co_consts[1].co_firstlineno
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        code.exec_code(space, w_d, w_d)
        w_fline = space.getitem(w_d, space.wrap('Aline'))
        assert space.int_w(w_fline) == 4

    def test_mangling(self):
        snippet = str(py.code.Source(r'''
            __g = "42"
            class X(object):
                def __init__(self, u):
                    self.__u = u
                def __f(__self, __n):
                    global __g
                    __NameError = NameError
                    try:
                        yield "found: " + __g
                    except __NameError as __e:
                        yield "not found: " + str(__e)
                    del __NameError
                    for __i in range(__self.__u * __n):
                        yield locals()
            result = X(2)
            assert not hasattr(result, "__f")
            result = list(result._X__f(3))
            assert len(result) == 7
            assert result[0].startswith("not found: ")
            for d in result[1:]:
                for key, value in d.items():
                    assert not key.startswith('__')
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)

    def test_ellipsis(self):
        snippet = str(py.code.Source(r'''
            d = {}
            d[...] = 12
            assert next(iter(d)) is Ellipsis
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        snip = "d[. . .]"
        space.raises_w(space.w_SyntaxError, self.compiler.compile,
                       snip, '<test>', 'exec', 0)

    def test_chained_access_augassign(self):
        snippet = str(py.code.Source(r'''
            class R(object):
               count = 0
            c = 0
            for i in [0,1,2]:
                c += 1
            r = R()
            for i in [0,1,2]:
                r.count += 1
            c += r.count
            l = [0]
            for i in [0,1,2]:
                l[0] += 1
            c += l[0]
            l = [R()]
            for i in [0]:
                l[0].count += 1
            c += l[0].count
            r.counters = [0]
            for i in [0,1,2]:
                r.counters[0] += 1
            c += r.counters[0]
            r = R()
            f = lambda : r
            for i in [0,1,2]:
                f().count += 1
            c += f().count
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        assert space.int_w(space.getitem(w_d, space.wrap('c'))) == 16

    def test_augassign_with_tuple_subscript(self):
        snippet = str(py.code.Source(r'''
            class D(object):
                def __getitem__(self, key):
                    assert key == self.lastkey
                    return self.lastvalue
                def __setitem__(self, key, value):
                    self.lastkey = key
                    self.lastvalue = value
            def one(return_me=[1]):
                return return_me.pop()
            d = D()
            a = 15
            d[1,2+a,3:7,...,1,] = 6
            d[one(),17,slice(3,7),...,1] *= 7
            result = d[1,17,3:7,Ellipsis,1]
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        assert space.int_w(space.getitem(w_d, space.wrap('result'))) == 42

    def test_continue_in_finally(self):
        space = self.space
        snippet = str(py.code.Source(r'''
def test():
    for abc in range(10):
        try: pass
        finally:
            continue       # 'continue' inside 'finally'

test()
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)

    def test_continue_in_nested_finally(self):
        space = self.space
        snippet = str(py.code.Source(r'''
def test():
    for abc in range(10):
        try: pass
        finally:
            try:
                continue       # 'continue' inside 'finally'
            except:
                pass
test()
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)

    def test_really_nested_stuff(self):
        space = self.space
        snippet = str(py.code.Source(r'''
            def f(self):
                def get_nested_class():
                    self
                    class Test(object):
                        def _STOP_HERE_(self):
                            return _STOP_HERE_(self)
                get_nested_class()
            f(42)
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        # assert did not crash

    def test_free_vars_across_class(self):
        space = self.space
        snippet = str(py.code.Source(r'''
            def f(x):
                class Test(object):
                    def meth(self):
                        return x + 1
                return Test()
            res = f(42).meth()
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        assert space.int_w(space.getitem(w_d, space.wrap('res'))) == 43

    def test_pick_global_names(self):
        space = self.space
        snippet = str(py.code.Source(r'''
            def f(x):
                def g():
                    global x
                    def h():
                        return x
                    return h()
                return g()
            x = "global value"
            res = f("local value")
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        w_res = space.getitem(w_d, space.wrap('res'))
        assert space.text_w(w_res) == "global value"

    def test_method_and_var(self):
        space = self.space
        snippet = str(py.code.Source(r'''
            def f():
                method_and_var = "var"
                class Test(object):
                    def method_and_var(self):
                        return "method"
                    def test(self):
                        return method_and_var
                return Test().test()
            res = f()
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        w_res = space.getitem(w_d, space.wrap('res'))
        assert space.eq_w(w_res, space.wrap("var"))
    
    def test_yield_from(self):
        space = self.space
        snippet = str(py.code.Source(r'''
            def f():
                def generator2():
                    yield 8
                def generator():
                    yield from generator2()
                return next(generator())
            res = f()
        '''))
        code = self.compiler.compile(snippet, '<tmp>', 'exec', 0)
        space = self.space
        w_d = space.newdict()
        space.exec_(code, w_d, w_d)
        w_res = space.getitem(w_d, space.wrap('res'))
        assert space.eq_w(w_res, space.wrap(8))

    def test_dont_inherit_flag(self):
        # this test checks that compile() don't inherit the __future__ flags
        # of the hosting code.
        space = self.space
        s1 = str(py.code.Source("""
            from __future__ import barry_as_FLUFL
            # not a syntax error inside the exec!
            exec(compile('x = 1 != 2', '?', 'exec', 0, 1))
        """))
        w_result = space.appexec([space.wrap(s1)], """(s1):
            ns = {}
            exec(s1, ns)
            return ns['x']
        """)
        assert space.is_true(w_result)

    def test_dont_inherit_across_import(self):
        from rpython.tool.udir import udir
        udir.join('test_dont_inherit_across_import.py').write('x = 1 != 2\n')
        space = self.space
        s1 = str(py.code.Source("""
            from __future__ import barry_as_FLUFL
            from test_dont_inherit_across_import import x
        """))
        w_result = space.appexec([space.wrap(str(udir)), space.wrap(s1)],
                                 """(udir, s1):
            import sys
            copy = sys.path[:]
            sys.path.insert(0, udir)
            ns = {}
            try:
                exec(s1, ns)
            finally:
                sys.path[:] = copy
            return ns['x']
        """)
        assert space.is_true(w_result)

    def test_filename_in_syntaxerror(self):
        e = py.test.raises(OperationError, self.compiler.compile, """if 1:
            'unmatched_quote
            """, 'hello_world', 'exec', 0)
        ex = e.value
        space = self.space
        assert ex.match(space, space.w_SyntaxError)
        assert 'hello_world' in space.text_w(space.str(ex.get_w_value(space)))

    def test_del_None(self):
        snippet = '''if 1:
            try:
                del None
            except NameError:
                pass
        '''
        e = py.test.raises(OperationError, self.compiler.compile,
                snippet, '<tmp>', 'exec', 0)
        ex = e.value
        space = self.space
        assert ex.match(space, space.w_SyntaxError)

    def test_from_future_import(self):
        source = """from __future__ import with_statement
with somtehing as stuff:
    pass
        """
        code = self.compiler.compile(source, '<filename>', 'exec', 0)
        assert isinstance(code, PyCode)
        assert code.co_filename == '<filename>'

        source2 = "with = 3"

        code = self.compiler.compile(source, '<filename2>', 'exec', 0)
        assert isinstance(code, PyCode)
        assert code.co_filename == '<filename2>'

    def test_assign_to_yield(self):
        code = 'def f(): (yield bar) += y'
        try:
            self.compiler.compile(code, '', 'single', 0)
        except OperationError as e:
            if not e.match(self.space, self.space.w_SyntaxError):
                raise
        else:
            py.test.fail("Did not raise")

    def test_invalid_genexp(self):
        code = 'dict(a = i for i in xrange(10))'
        try:
            self.compiler.compile(code, '', 'single', 0)
        except OperationError as e:
            if not e.match(self.space, self.space.w_SyntaxError):
                raise
        else:
            py.test.fail("Did not raise")

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

