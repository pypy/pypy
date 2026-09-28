
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

def test_co_positions_no_debug_ranges():
    import sys
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

def test_constructor_argument_order():
    # CodeType's positional argument order must match CPython's:
    # ..., linetable, exceptiontable, freevars=(), cellvars=()
    def func():
        try:
            x = 1
        except ValueError:
            x = 2
        return x
    co = func.__code__
    assert co.co_exceptiontable != b''
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
