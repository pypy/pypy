"""Test the exec statement functionality.

New for PyPy - Could be incorporated into CPython regression tests.
"""
import autopath


def test_file(space):
    space.appexec([space.wrap(__file__)], '''
        (filename):
            fo = open(filename, 'r')
            g = {}
            exec fo in g
            assert 'test_file' in g
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
