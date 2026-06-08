
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
