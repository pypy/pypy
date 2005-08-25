"""Test the exec statement functionality.

New for PyPy - Could be incorporated into CPython regression tests.
"""
import autopath
from pypy.tool.udir import udir


def test_file(space):
    fn = udir.join('test_exec_file')
    fn.write('abc=1\ncba=2\n')
    space.appexec([space.wrap(str(fn))], '''
        (filename):
            fo = open(filename, 'r')
            g = {}
            exec fo in g
            assert 'abc' in g
            assert 'cba' in g
    ''')


class AppTestExecStmt: 

    def test_string(self):
        g = {}
        l = {}
        exec "a = 3" in g, l
        assert l['a'] == 3

    def test_localfill(self):
        g = {}
        exec "a = 3" in g
        assert g['a'] == 3
        
    def test_builtinsupply(self):
        g = {}
        exec "pass" in g
        assert g.has_key('__builtins__')

    def test_invalidglobal(self):
        def f():
            exec 'pass' in 1
        raises(TypeError,f)

    def test_invalidlocal(self):
        def f():
            exec 'pass' in {}, 2
        raises(TypeError,f)

    def test_codeobject(self):
        co = compile("a = 3", '<string>', 'exec')
        g = {}
        l = {}
        exec co in g, l
        assert l['a'] == 3

    def test_implicit(self):
        a = 4
        exec "a = 3"
        assert a == 3

    def test_tuplelocals(self):
        g = {}
        l = {}
        exec ("a = 3", g, l)
        assert l['a'] == 3
        
    def test_tupleglobals(self):
        g = {}
        exec ("a = 3", g)
        assert g['a'] == 3

    def test_exceptionfallthrough(self):
        def f():
            exec 'raise TypeError' in {}
        raises(TypeError,f)

    def test_global_stmt(self):
        g = {}
        l = {}
        co = compile("global a; a=5", '', 'exec')
        #import dis
        #dis.dis(co)
        exec co in g, l
        assert l == {}
        assert g['a'] == 5

    def test_specialcase_free_load(self):
        exec """if 1:
            def f():
                exec 'a=3'
                return a
            x = f()
        """
        assert x == 3

    def test_specialcase_free_load2(self):
        exec """if 1:
            def f(a):
                exec 'a=3'
                return a
            x = f(4)
        """
        assert x == 3

    def test_specialcase_globals_and_exec(self):
        d = {}
        exec """if 1:
            b = 2
            c = 3 
            d = 4 
            def f(a):
                global b
                exec 'd=42 ; b=7'
                return a,b,c,d
            #import dis
            #dis.dis(f)
            res = f(3)
        """ in d
        r = d['res']
        assert r == (3,2,3,42)

    def test_nested_names_are_not_confused(self):
        def get_nested_class():
            method_and_var = "var"
            class Test:
                def method_and_var(self):
                    return "method"
                def test(self):
                    return method_and_var
                def actual_global(self):
                    return str("global")
                def str(self):
                    return str(self)
            return Test()
        t = get_nested_class()
        assert t.actual_global() == "global" 
        assert t.test() == 'var'
        assert t.method_and_var() == 'method'

    def test_import_star_shadows_global(self):
        d = {'platform' : 3}
        exec """if 1:
            def f():
                from sys import *
                return platform
            res = f()""" in d
        import sys
        assert d['res'] == sys.platform

    def test_import_global_takes_precendence(self):
        d = {'platform' : 3}
        exec """if 1:
            def f():
                global platform
                from sys import *
                return platform
            res = f()""" in d
        import sys
        assert d['platform'] == 3

    def test_exec_load_name(self):
        d = {'x': 2}
        exec """if 1:
            def f():
                save = x 
                exec "x=3"
                return x,save
        """ in d
        res = d['f']()
        assert res == (3, 2)
