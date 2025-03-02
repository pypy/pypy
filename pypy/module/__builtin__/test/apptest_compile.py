from pytest import raises, mark
import sys

def test_simple():
    co = compile('1+2', '?', 'eval')
    assert eval(co) == 3
    co = compile(memoryview(b'1+2'), '?', 'eval')
    assert eval(co) == 3
    exc = raises(SyntaxError, compile, chr(0), '?', 'eval')
    assert str(exc.value) == "source code string cannot contain null bytes"
    compile("from __future__ import with_statement", "<test>", "exec")
    raises(SyntaxError, compile, '-', '?', 'eval')
    raises(SyntaxError, compile, '"\\xt"', '?', 'eval')
    raises(ValueError, compile, '1+2', '?', 'maybenot')
    raises(ValueError, compile, "\n", "<string>", "exec", 0xff)
    raises(TypeError, compile, '1+2', 12, 34)

def test_error_message():
    compile('# -*- coding: iso-8859-15 -*-\n', 'dummy', 'exec')
    compile(b'\xef\xbb\xbf\n', 'dummy', 'exec')
    compile(b'\xef\xbb\xbf# -*- coding: utf-8 -*-\n', 'dummy', 'exec')
    exc = raises(SyntaxError, compile,
        b'# -*- coding: fake -*-\n', 'dummy', 'exec')
    assert 'fake' in str(exc.value)
    exc = raises(SyntaxError, compile,
        b'\xef\xbb\xbf# -*- coding: iso-8859-15 -*-\n', 'dummy', 'exec')
    assert 'iso-8859-15' in str(exc.value)
    assert 'BOM' in str(exc.value)
    exc = raises(SyntaxError, compile,
        b'\xef\xbb\xbf# -*- coding: fake -*-\n', 'dummy', 'exec')
    assert 'fake' in str(exc.value)
    assert 'BOM' in str(exc.value)

def test_unicode():
    try:
        compile(u'-', '?', 'eval')
    except SyntaxError as e:
        assert e.lineno == 1

def test_incorrect_escape_deprecation_bytes():
    import warnings
    with warnings.catch_warnings(record=True) as l:
        warnings.simplefilter('always', category=DeprecationWarning)
        compile(r"b'\}'", '', 'exec')
    assert len(l) == 1

def test_unicode_encoding():
    code = "# -*- coding: utf-8 -*-\npass\n"
    compile(code, "tmp", "exec")

def test_bytes():
    code = b"# -*- coding: utf-8 -*-\npass\n"
    compile(code, "tmp", "exec")
    c = compile(b"# coding: latin1\nfoo = 'caf\xe9'\n", "<string>", "exec")
    ns = {}
    exec(c, ns)
    assert ns['foo'] == 'café'
    assert eval(b"# coding: latin1\n'caf\xe9'\n") == 'café'

def test_memoryview():
    m = memoryview(b'2 + 1')
    co = compile(m, 'baz', 'eval')
    assert eval(co) == 3
    assert eval(m) == 3
    ns = {}
    exec(memoryview(b'r = 2 + 1'), ns)
    assert ns['r'] == 3

def test_recompile_ast():
    import _ast
    # raise exception when node type doesn't match with compile mode
    co1 = compile('print(1)', '<string>', 'exec', _ast.PyCF_ONLY_AST)
    raises(TypeError, compile, co1, '<ast>', 'eval')
    co2 = compile('1+1', '<string>', 'eval', _ast.PyCF_ONLY_AST)
    tree = compile(co2, '<ast>', 'eval')
    assert compile(co2, '<ast>', 'eval', _ast.PyCF_ONLY_AST) is co2

def test_leading_newlines():
    src = """
def fn(): pass
"""
    co = compile(src, 'mymod', 'exec')
    firstlineno = co.co_firstlineno
    assert firstlineno == 1

def test_null_bytes():
    raises(ValueError, compile, '\x00', 'mymod', 'exec', 0)
    src = "#abc\x00def\n"
    raises(ValueError, compile, src, 'mymod', 'exec')
    raises(ValueError, compile, src, 'mymod', 'exec', 0)

@mark.pypy_only
def test_null_bytes_flag():
    from _ast import PyCF_ACCEPT_NULL_BYTES
    raises(SyntaxError, compile, '\x00', 'mymod', 'exec',
            PyCF_ACCEPT_NULL_BYTES)
    src = "#abc\x00def\n"
    compile(src, 'mymod', 'exec', PyCF_ACCEPT_NULL_BYTES)  # works

def test_compile_regression():
    """Clone of the part of the original test that was failing."""
    import ast

    codestr = '''def f():
    """doc"""
    try:
        assert False
    except AssertionError:
        return (True, f.__doc__, __debug__)
    else:
        return (False, f.__doc__, __debug__)
    '''

    def f():
        """doc"""

    values = [(-1, __debug__, f.__doc__, __debug__),
        (0, True, 'doc', True),
        (1, False, 'doc', False),
        (2, False, None, False)]

    for optval, *expected in values:
        # test both direct compilation and compilation via AST
        codeobjs = []
        codeobjs.append(compile(codestr, "<test>", "exec", optimize=optval))
        tree = ast.parse(codestr)
        codeobjs.append(compile(tree, "<test>", "exec", optimize=optval))
        for i, code in enumerate(codeobjs):
            print(optval, *expected, i)
            ns = {}
            exec(code, ns)
            rv = ns['f']()
            print(rv)
            assert rv == tuple(expected)

def test_assert_remove():
    """Test removal of the asserts with optimize=1."""
    import ast

    code = """def f():
    assert False
    """
    tree = ast.parse(code)
    for to_compile in [code, tree]:
        compiled = compile(to_compile, "<test>", "exec", optimize=1)
        ns = {}
        exec(compiled, ns)
        ns['f']()

def test_docstring_remove():
    """Test removal of docstrings with optimize=2."""
    import ast
    import marshal

    code = """
'module_doc'

def f():
    'func_doc'

class C:
    'class_doc'
"""
    tree = ast.parse(code)
    for to_compile in [code, tree]:
        compiled = compile(to_compile, "<test>", "exec", optimize=2)

        ns = {}
        exec(compiled, ns)
        assert '__doc__' not in ns
        assert ns['f'].__doc__ is None
        assert ns['C'].__doc__ is None

        # Check that the docstrings are gone from the bytecode and not just
        # inaccessible.
        marshalled = str(marshal.dumps(compiled))
        assert 'module_doc' not in marshalled
        assert 'func_doc' not in marshalled
        assert 'class_doc' not in marshalled

def test_build_class():
    """Test error message bad __prepare__"""

    class BadMeta(type):
        @classmethod
        def __prepare__(*args):
            return None

    def func():
        class Foo(metaclass=BadMeta):
            pass

    excinfo = raises(TypeError, func)
    assert str(excinfo.value) == (
        r"BadMeta.__prepare__() must return a mapping, not NoneType"
    )

@mark.pypy_only
def test_make_sure_namespace_in_class_is_moduledict():
    import __pypy__
    class A:
        assert __pypy__.strategy(locals()) == "ModuleDictStrategy"

def test_compile_feature_version():
    co = compile('1+2', '?', 'eval', _feature_version=-1)
    assert eval(co) == 3

    co = compile('1+2', '?', 'eval', _feature_version=8)
    assert eval(co) == 3


@mark.pypy_only
def test_ignore_cookie():
    # make sure the latin1 cookie is ignored
    from _ast import PyCF_IGNORE_COOKIE
    src = """# coding: latin1
def fn(): return '%s'
""" % chr(230)

    co = compile(src, "<string>", "exec", PyCF_IGNORE_COOKIE)
    ns = {}
    eval(co, ns)
    assert ns['fn']() == '%s' % chr(230)


def test_weird_globals_builtins_eval():
    class MyGlobals(dict):
        def __missing__(self, key):
            assert key != '__builtins__'
            return int(key.removeprefix("_number_"))

    code = "lambda: " + "+".join(f"_number_{i}" for i in range(1000))
    sum_1000 = eval(code, MyGlobals())
    expected = sum(range(1000))
    assert sum_1000() == expected

def test_exec_with_closure():
    from types import CellType

    def function_without_closures():
        return 3 * 5

    result = 0
    def make_closure_functions():
        a = 2
        b = 3
        c = 5
        def three_freevars():
            nonlocal result
            nonlocal a
            nonlocal b
            result = a*b
        def four_freevars():
            nonlocal result
            nonlocal a
            nonlocal b
            nonlocal c
            result = a*b*c
        return three_freevars, four_freevars
    three_freevars, four_freevars = make_closure_functions()

    # "smoke" test
    result = 0
    exec(three_freevars.__code__,
        three_freevars.__globals__,
        closure=three_freevars.__closure__)
    assert result == 6

    # should also work with a manually created closure
    result = 0
    my_closure = (CellType(35), CellType(72), three_freevars.__closure__[2])
    exec(three_freevars.__code__,
        three_freevars.__globals__,
        closure=my_closure)

    assert result == 2520

def test_exec_with_closure_errors():
    from types import CellType
    def f(a, b):
        def g():
            print(a, b)
            return a + b
        return g

    g = f(1, 2)

    locals = globals = {'a': 12, 'b': 23}
    with raises(TypeError) as info:
        exec(g.__code__, locals, globals)
    assert str(info.value) == "code object requires a closure of exactly length 2"

    my_closure = (CellType(35), CellType(72), CellType(100))
    with raises(TypeError) as info:
        exec(g.__code__, locals, globals, closure=my_closure)
    assert str(info.value) == "code object requires a closure of exactly length 2"

    def f():
        pass
    with raises(TypeError) as info:
        exec(f.__code__, locals, globals, closure=my_closure)
    assert str(info.value) == "cannot use a closure with this code object"

    with raises(TypeError) as info:
        exec('print(1)', locals, globals, closure=my_closure)
    assert str(info.value) == "closure can only be used when source is a code object"


def test_exec_with_closure_dont_overwrite_cell_vars_from_locals():
    def f(a, b):
        def g():
            print(a, b)
            return a + b
        return g

    g = f(1, 2)

    locals = globals = {'a': 12, 'b': 23}
    print(exec(g.__code__, locals, globals, closure=g.__closure__))
    print(g.__closure__)
