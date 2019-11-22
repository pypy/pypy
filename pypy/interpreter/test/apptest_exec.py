"""Test the exec statement functionality.

New for PyPy - Could be incorporated into CPython regression tests.
"""
import pytest

def test_string():
    g = {}
    l = {}
    exec "a = 3" in g, l
    assert l['a'] == 3

def test_localfill():
    g = {}
    exec "a = 3" in g
    assert g['a'] == 3

def test_builtinsupply():
    g = {}
    exec "pass" in g
    assert g.has_key('__builtins__')

def test_invalidglobal():
    with pytest.raises(TypeError):
        exec 'pass' in 1

def test_invalidlocal():
    with pytest.raises(TypeError):
        exec 'pass' in {}, 2

def test_codeobject():
    co = compile("a = 3", '<string>', 'exec')
    g = {}
    l = {}
    exec co in g, l
    assert l['a'] == 3

def test_implicit():
    a = 4
    exec "a = 3"
    assert a == 3

def test_tuplelocals():
    g = {}
    l = {}
    exec ("a = 3", g, l)
    assert l['a'] == 3

def test_tupleglobals():
    g = {}
    exec ("a = 3", g)
    assert g['a'] == 3

def test_exceptionfallthrough():
    with pytest.raises(TypeError):
        exec 'raise TypeError' in {}

def test_global_stmt():
    g = {}
    l = {}
    co = compile("global a; a=5", '', 'exec')
    #import dis
    #dis.dis(co)
    exec co in g, l
    assert l == {}
    assert g['a'] == 5

def test_specialcase_free_load():
    exec """if 1:
        def f():
            exec 'a=3'
            return a
        x = f()\n"""
    assert x == 3

def test_specialcase_free_load2():
    exec """if 1:
        def f(a):
            exec 'a=3'
            return a
        x = f(4)\n"""
    assert x == 3

def test_specialcase_globals_and_exec():
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

def test_nested_names_are_not_confused():
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

def test_import_star_shadows_global():
    d = {'platform' : 3}
    exec """if 1:
        def f():
            from sys import *
            return platform
        res = f()\n""" in d
    import sys
    assert d['res'] == sys.platform

def test_import_global_takes_precendence():
    d = {'platform' : 3}
    exec """if 1:
        def f():
            global platform
            from sys import *
            return platform
        res = f()\n""" in d
    import sys
    assert d['platform'] == 3

def test_exec_load_name():
    d = {'x': 2}
    exec """if 1:
        def f():
            save = x
            exec "x=3"
            return x,save
    \n""" in d
    res = d['f']()
    assert res == (3, 2)

def test_space_bug():
    d = {}
    exec "x=5 " in d
    assert d['x'] == 5

def test_synerr():
    with pytest.raises(SyntaxError):
        exec "1 2"

def test_mapping_as_locals():
    import sys
    if not hasattr(sys, 'pypy_objspaceclass'):
        skip("need PyPy for non-dictionaries in exec statements")
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
    exec "y=n" in m   # NOTE: this doesn't work in CPython
    assert m.result == {'x': 'm', 'y': 'n'}

def test_filename():
    with pytest.raises(SyntaxError) as excinfo:
        exec "'unmatched_quote"
    assert excinfo.value.filename == '<string>'
    with pytest.raises(SyntaxError) as excinfo:
        eval("'unmatched_quote")
    assert excinfo.value.filename == '<string>'

def test_exec_and_name_lookups():
    ns = {}
    exec """def f():
        exec 'x=1' in locals()
        return x""" in ns

    f = ns['f']
    assert f() == 1

def test_exec_unicode():
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

def test_eval_unicode():
    u = "u'%s'" % unichr(0x1234)
    v = eval(u)
    assert v == unichr(0x1234)

def test_compile_unicode():
    s = "x = u'\xd0\xb9\xd1\x86\xd1\x83\xd0\xba\xd0\xb5\xd0\xbd'"
    u = s.decode('utf-8')
    c = compile(u, '<input>', 'exec')
    exec c
    assert len(x) == 6
    assert ord(x[0]) == 0x0439

def test_nested_qualified_exec():
    import sys
    if sys.version_info < (2, 7, 9):
        skip()
    code = ["""
def g():
    def f():
        if True:
            exec "" in {}, {}
    """, """
def g():
    def f():
        if True:
            exec("", {}, {})
    """]
    for c in code:
        compile(c, "<code>", "exec")

def test_exec_tuple():
    # note: this is VERY different than testing exec("a = 42", d), because
    # this specific case is handled specially by the AST compiler
    d = {}
    x = ("a = 42", d)
    exec x
    assert d['a'] == 42
