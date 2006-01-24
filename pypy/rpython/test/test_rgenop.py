from pypy.rpython.rgenop import *
from pypy.rpython.lltypesystem.lltype import *


def test_square():
    """def square(v0): return v0*v0"""
    startlink = newgraph("square")
    block = newblock()
    v0 = geninputarg(block, Signed)
    v1 = genop(block, 'int_mul', [v0, v0], Signed)
    link = newreturnlink(block, v1)
    closeblock1(block, link)
    closelink(startlink, block)

    res = runlink(startlink, [17])
    assert res == 289

def test_if():
    """
    def f(v0):
        if v0 < 0:
            return 0
        else:
            return v0
    """
    startlink = newgraph("if")
    block = newblock()
    v0 = geninputarg(block, Signed)
    const0 = genconst(block, 0)
    v1 = genop(block, 'int_lt', [v0, const0], Bool)
    true_link = newreturnlink(block, const0)
    false_link = newreturnlink(block, v0)
    closeblock2(block, v1, false_link, true_link)
    closelink(startlink, block)

    res = runlink(startlink, [-1])
    assert res == 0
    res = runlink(startlink, [42])
    assert res == 42
