from pytest import raises
from pypy.tool.pytest.astrewriter import ast_rewrite

def get_assert_explanation(space, src):
    fn = "?"
    w_code = ast_rewrite.rewrite_asserts(space, src, fn)
    w_d = space.newdict()
    excinfo = space.raises_w(space.w_AssertionError, space.exec_, w_code, w_d, w_d)
    return space.text_w(space.getitem(space.getattr(excinfo.value.get_w_value(space), space.newtext("args")), space.newint(0)))

def test_simple(space):
    src = """
x = 1
def f():
    y = 2
    assert x == y
f()
"""
    expl = get_assert_explanation(space, src)
    assert expl == 'assert 1 == 2'

def test_call(space):
    src = """
x = 1
def g():
    return 15
def f():
    y = 2
    assert g() == x + y
f()
"""
    expl = get_assert_explanation(space, src)
    assert expl == 'assert 15 == (1 == 2)\n +  where 15 = g()'

def test_list(space):

    src = """
x = 1
y = 2
assert [1, 1, x] == [1, 1, y]
"""
    expl = get_assert_explanation(space, src)
    # diff etc disabled for now
    assert expl == 'assert [1, 1, 1] == [1, 1, 2]'
