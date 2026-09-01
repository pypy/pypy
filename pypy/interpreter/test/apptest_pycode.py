
import pytest

def test_invalid_positions_dont_crash():
    def f(a, b):
        return a / b

    c = f.__code__.replace(co_linetable=b'\xff')
    list(c.co_lines()) # these must not crash
    list(c.co_positions())
    c.co_lnotab


class Qualname:
    f = lambda self: 1

double_lambda = lambda : (lambda : 1)

def test_co_qualname():
    def f():
        pass
    assert f.__code__.co_qualname == "test_co_qualname.<locals>.f"
    assert Qualname.f.__code__.co_qualname == "Qualname.<lambda>"
    inner = double_lambda()
    assert inner.__code__.co_qualname == "<lambda>.<locals>.<lambda>"

def test_replace_co_qualname():
    co = compile("x = x + 1", 'baz', 'exec')
    assert co.co_qualname == "<module>"
    co2 = co.replace(co_qualname="abc")
    assert co2.co_qualname == "abc"

def test_attributes():
    def f(): pass
    def g(x, *y, **z): "docstring"
    assert hasattr(f.__code__, 'co_code')
    assert hasattr(g.__code__, 'co_code')

    testcases = [
        (f.__code__, {'co_name': 'f',
                       'co_names': (),
                       'co_varnames': (),
                       'co_argcount': 0,
                       'co_posonlyargcount': 0,
                       'co_kwonlyargcount': 0,
                       'co_consts': (None,)
                       }),
        (g.__code__, {'co_name': 'g',
                       'co_names': (),
                       'co_varnames': ('x', 'y', 'z'),
                       'co_argcount': 1,
                       'co_posonlyargcount': 0,
                       'co_kwonlyargcount': 0,
                       'co_consts': ("docstring", None),
                       }),
        ]

    import sys
    if hasattr(sys, 'pypy_objspaceclass'):
        testcases += [
            (abs.__code__, {'co_name': 'abs',
                             'co_varnames': ('val',),
                             'co_argcount': 1,
                             'co_posonlyargcount': 0,
                             'co_kwonlyargcount': 0,
                             'co_flags': 0,
                             'co_consts': ("abs(number) -> number\n\nReturn the absolute value of the argument.",),
                             }),
            (object.__init__.__code__,
                            {#'co_name': '__init__',   XXX getting descr__init__
                             'co_varnames': ('obj', 'args', 'keywords'),
                             'co_argcount': 1,
                             'co_posonlyargcount': 0,
                             'co_kwonlyargcount': 0,
                             'co_flags': 0x000C,  # VARARGS|VARKEYWORDS
                             }),
            ]

    # in PyPy, built-in functions have code objects
    # that emulate some attributes
    for code, expected in testcases:
        assert hasattr(code, '__class__')
        assert not hasattr(code, '__dict__')
        for key, value in expected.items():
            assert getattr(code, key) == value

def test_co_names():
    src = '''if 1:
    def foo():
        pass

    g = 3

    def f(x, y):
        z = x + y
        foo(g)
'''
    d = {}
    exec(src, d)

    assert list(sorted(d['f'].__code__.co_names)) == ['foo', 'g']

def test_hash():
    d1 = {}
    exec("def f(): pass", d1)
    d2 = {}
    exec("def f(): pass", d2)
    assert d1['f'].__code__ == d2['f'].__code__
    assert hash(d1['f'].__code__) == hash(d2['f'].__code__)

def test_repr():
    def f():
        xxx
    res = repr(f.__code__)
    assert res.startswith("<code object f at 0x")
    assert ', file "%s", line ' % f.__code__.co_filename in res
    assert res.endswith('>')

def test_code_extra():
    # CPython 3.12 stopped setting CO_NOFREE on code objects, so PyPy
    # doesn't either
    CO_NOFREE = 0x0040
    assert not (compile("x = x + 1", 'baz', 'exec').co_flags & CO_NOFREE)

    d = {}
    exec("""if 1:
    def f():
        "docstring"
        'stuff'
        56
""", d)

    assert not (d['f'].__code__.co_flags & CO_NOFREE)

    exec("""if 1:
    def f(x):
        def g(y):
            return x+y
        return g
""", d)

    # CO_NESTED
    assert d['f'](4).__code__.co_flags & 0x10
    assert d['f'].__code__.co_flags & 0x10 == 0

def test_code_eq_non_code():
    class A(object):
        def __eq__(self, other):
            return 23
        def __ne__(self, other):
            return 41
    def f(): pass
    assert (f.__code__ == A()) == 23
    assert (f.__code__ != A()) == 41

def test_issue1844():
    import types
    args = (1, 0, 0, 1, 0, 0, b'', (), (), ('a',), '', 'operator', 'operator', 0, b'', b'')
    # previously raised a MemoryError when translated
    types.CodeType(*args)

def test_co_lnotab_is_deprecated():
    import warnings
    co = compile("x = x + 1", 'baz', 'exec')
    with warnings.catch_warnings(record=True) as l:
        warnings.simplefilter('always', category=DeprecationWarning)
        co.co_lnotab
    assert len(l) == 1
    assert issubclass(l[0].category, DeprecationWarning)

def test_constructor_argument_order():
    # CodeType's positional argument order must match CPython's:
    # ..., linetable, exceptiontable, freevars=(), cellvars=()
    def func():
        x = 1
        return x
    co = func.__code__
    CodeType = type(co)
    co2 = CodeType(co.co_argcount,
                    co.co_posonlyargcount,
                    co.co_kwonlyargcount,
                    co.co_nlocals,
                    co.co_stacksize,
                    co.co_flags,
                    co.co_code,
                    co.co_consts,
                    co.co_names,
                    co.co_varnames,
                    co.co_filename,
                    co.co_name,
                    co.co_qualname,
                    co.co_firstlineno,
                    co.co_linetable,
                    co.co_exceptiontable,
                    co.co_freevars,
                    co.co_cellvars)
    assert co2.co_freevars == co.co_freevars
    assert co2.co_cellvars == co.co_cellvars
    assert co2.co_exceptiontable == co.co_exceptiontable

def test_nlocals_mismatch():
    def func():
        x = 1
        return x
    co = func.__code__
    assert co.co_nlocals > 0

    CodeType = type(co)
    for diff in (-1, 1):
        with pytest.raises(ValueError):
            CodeType(co.co_argcount,
                     co.co_posonlyargcount,
                     co.co_kwonlyargcount,
                     co.co_nlocals + diff,
                     co.co_stacksize,
                     co.co_flags,
                     co.co_code,
                     co.co_consts,
                     co.co_names,
                     co.co_varnames,
                     co.co_filename,
                     co.co_name,
                     co.co_qualname,
                     co.co_firstlineno,
                     co.co_linetable,
                     co.co_exceptiontable,
                     co.co_freevars,
                     co.co_cellvars)

    with pytest.raises(ValueError):
        co.replace(co_nlocals=co.co_nlocals - 1)
    with pytest.raises(ValueError):
        co.replace(co_nlocals=co.co_nlocals + 1)

def test_code_equality():
    def f():
        try:
            a()
        except:
            b()
        else:
            c()
        finally:
            d()
    code_a = f.__code__
    code_b = code_a.replace(co_linetable=b"")
    code_c = code_a.replace(co_exceptiontable=b"")
    code_d = code_b.replace(co_exceptiontable=b"")
    assert code_a != code_b
    assert code_a != code_c
    assert code_a != code_d
    assert code_b != code_c
    assert code_b != code_d
    assert code_c != code_d

def test_invalid_bytecode():
    def foo():
        pass

    foo.__code__ = foo.__code__.replace(
        co_code=b'\xe5' + foo.__code__.co_code[1:])

    with pytest.raises(SystemError):
        foo()

def test_replace():
    co = compile("x = x + 1", 'baz', 'exec')
    co2 = co.replace(co_flags=co.co_flags | 0x100)
    assert co2.co_name == co.co_name # in theory need to check them all
    assert co2.co_flags == co.co_flags | 0x100

    with pytest.raises(TypeError):
        co.replace(1)
    with pytest.raises(TypeError):
        co.replace(abc=123)

def test_varname_from_oparg():
    import sys
    if '__pypy__' not in sys.builtin_module_names:
        # CPython deduplicates a variable that is both a regular local and
        # a cellvar into a single localsplus slot; PyPy doesn't, so the
        # slot count (and _varname_from_oparg bounds) differ.
        return
    def outer(cell):
        def inner(x):
            return cell
        return inner

    inner = outer(42)

    for (c, e_varnames, e_cellvars, e_freevars) in [
        (outer.__code__, ('cell', 'inner',), ('cell',), ()),
        (inner.__code__, ('x',), (), ('cell',)),
    ]:
        print(c.co_varnames, c.co_cellvars, c.co_freevars)
        assert c.co_varnames == e_varnames
        assert c.co_cellvars == e_cellvars
        assert c.co_freevars == e_freevars
        localsplus = e_varnames + e_cellvars + e_freevars
        assert tuple(c._varname_from_oparg(i) for i in range(len(localsplus))) == localsplus
        pytest.raises(IndexError, c._varname_from_oparg, -1)
        pytest.raises(IndexError, c._varname_from_oparg, len(localsplus))

def test_co_positions_no_debug_ranges():
    import sys
    if '__pypy__' not in sys.builtin_module_names:
        # CPython doesn't blank out column info for no_debug_ranges the
        # same way PyPy does
        return
    def f():
        x = 1
        return x
    saved = sys._xoptions.copy()
    try:
        sys._xoptions['no_debug_ranges'] = True
        for line, end_line, column, end_column in f.__code__.co_positions():
            if line is None:
                continue
            assert line == end_line
            assert column is None
            assert end_column is None
    finally:
        sys._xoptions.clear()
        sys._xoptions.update(saved)
