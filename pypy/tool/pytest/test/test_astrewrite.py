from pytest import raises
from pypy.tool.pytest.astrewriter import ast_rewrite

def test_simple(space):
    src = """
x = 1
def f():
    y = 2
    assert x == y
f()
"""
    fn = "?"
    w_code = ast_rewrite.rewrite_asserts(space, src, fn)
    w_d = space.newdict()
    space.raises_w(space.w_AssertionError, space.exec_, w_code, w_d, w_d)


