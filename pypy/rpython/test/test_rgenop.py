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

def test_loop():
    """
    def f(v0):
        i = 1
        result = 1
        while i <= v0:
            result *= i
            i += 1
        return result
    """
    startlink = newgraph("loop")
    block = newblock()
    v0 = geninputarg(block, Signed)
    const1 = genconst(block, 1)
    link = newlink(block, [const1, const1, v0])
    closeblock1(block, link)
    closelink(startlink, block)
    loopblock = newblock()
    result0 = geninputarg(loopblock, Signed)
    i0 = geninputarg(loopblock, Signed)
    v1 = geninputarg(loopblock, Signed)
    closelink(link, loopblock)
    const1 = genconst(block, 1)
    result1 = genop(loopblock, 'int_mul', [result0, i0], Signed)
    i1 = genop(loopblock, 'int_add', [i0, const1], Signed)
    v2 = genop(loopblock, 'int_le', [i1, v1], Bool)
    false_link = newreturnlink(loopblock, result1)
    true_link = newlink(loopblock, [result1, i1, v1])
    closelink(true_link, loopblock)
    closeblock2(loopblock, v2, false_link, true_link)
    res = runlink(startlink, [0])
    assert res == 1
    res = runlink(startlink, [1])
    assert res == 1
    res = runlink(startlink, [7])
    assert res == 5040
