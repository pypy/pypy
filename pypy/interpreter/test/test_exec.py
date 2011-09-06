"""Test the exec statement functionality.

New for PyPy - Could be incorporated into CPython regression tests.
"""
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
            x = f()\n"""
        assert x == 3

    def test_specialcase_free_load2(self):
        exec """if 1:
            def f(a):
                exec 'a=3'
                return a
            x = f(4)\n"""
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
            res = f(3)\n""" in d
        r = d['res']
        assert r == (3,2,3,42)

    def test_nested_names_are_not_confused(self):
        def get_nested_class():
            method_and_var = "var"
            class Test(object):
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
            res = f()\n""" in d
        import sys
        assert d['res'] == sys.platform

    def test_import_global_takes_precendence(self):
        d = {'platform' : 3}
        exec """if 1:
            def f():
                global platform
                from sys import *
                return platform
            res = f()\n""" in d
        import sys
        assert d['platform'] == 3

    def test_exec_load_name(self):
        d = {'x': 2}
        exec """if 1:
            def f():
                save = x 
                exec "x=3"
                return x,save
        \n""" in d
        res = d['f']()
        assert res == (3, 2)

    def test_space_bug(self):
        d = {}
        exec "x=5 " in d
        assert d['x'] == 5

    def test_synerr(self):
        def x():
            exec "1 2"
        raises(SyntaxError, x)

    def test_mapping_as_locals(self):
        import sys
        if sys.version_info < (2,5) or not hasattr(sys, 'pypy_objspaceclass'):
            skip("need CPython 2.5 or PyPy for non-dictionaries in exec statements")
        class M(object):
            def __getitem__(self, key):
                return key
            def __setitem__(self, key, value):
                self.result[key] = value
            def setdefault(self, key, value):
                assert key == '__builtins__'
        m = M()
        m.result = {}
        exec "x=m" in {}, m
        assert m.result == {'x': 'm'}
        exec "y=n" in m   # NOTE: this doesn't work in CPython 2.4
        assert m.result == {'x': 'm', 'y': 'n'}

    def test_filename(self):
        try:
            exec "'unmatched_quote"
        except SyntaxError, msg:
            assert msg.filename == '<string>'
        try:
            eval("'unmatched_quote")
        except SyntaxError, msg:
            assert msg.filename == '<string>'

    def test_exec_and_name_lookups(self):
        ns = {}
        exec """def f():
        exec 'x=1' in locals()
        return x
""" in ns

        f = ns['f']

        try:
            res = f()
        except NameError, e: # keep py.test from exploding confused
            raise e

        assert res == 1

    def test_exec_unicode(self):
        # 's' is a string
        s = "x = u'\xd0\xb9\xd1\x86\xd1\x83\xd0\xba\xd0\xb5\xd0\xbd'"
        # 'u' is a unicode
        u = s.decode('utf-8')
        exec u
        assert len(x) == 6
        assert ord(x[0]) == 0x0439
        assert ord(x[1]) == 0x0446
        assert ord(x[2]) == 0x0443
        assert ord(x[3]) == 0x043a
        assert ord(x[4]) == 0x0435
        assert ord(x[5]) == 0x043d

    def test_eval_unicode(self):
        u = "u'%s'" % unichr(0x1234)
        v = eval(u)
        assert v == unichr(0x1234)

    def test_compile_unicode(self):
        s = "x = u'\xd0\xb9\xd1\x86\xd1\x83\xd0\xba\xd0\xb5\xd0\xbd'"
        u = s.decode('utf-8')
        c = compile(u, '<input>', 'exec')
        exec c
        assert len(x) == 6
        assert ord(x[0]) == 0x0439
