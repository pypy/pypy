from pypy.rpython.rgenop import *
from pypy.rpython.lltypesystem.lltype import *


def test_square():
    """def square(v0): return v0*v0"""
    block = newblock()
    v0 = geninputarg(block, Signed)
    v1 = genop(block, 'int_mul', [v0, v0], Signed)
    link = closeblock1(block)
    closereturnlink(link, v1)

    res = runblock(block, [17])
    assert res == 289

def test_if():
    """
    def f(v0):
        if v0 < 0:
            return 0
        else:
            return v0
    """
    block = newblock()
    v0 = geninputarg(block, Signed)
    const0 = genconst(block, 0)
    v1 = genop(block, 'int_lt', [v0, const0], Bool)
    false_link, true_link = closeblock2(block, v1)
    closereturnlink(true_link, const0)
    closereturnlink(false_link, v0)

    res = runblock(block, [-1])
    assert res == 0
    res = runblock(block, [42])
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
    block = newblock()
    v0 = geninputarg(block, Signed)
    const1 = genconst(block, 1)
    link = closeblock1(block)
    loopblock = newblock()
    result0 = geninputarg(loopblock, Signed)
    i0 = geninputarg(loopblock, Signed)
    v1 = geninputarg(loopblock, Signed)
    closelink(link, [const1, const1, v0], loopblock)
    const1 = genconst(block, 1)
    result1 = genop(loopblock, 'int_mul', [result0, i0], Signed)
    i1 = genop(loopblock, 'int_add', [i0, const1], Signed)
    v2 = genop(loopblock, 'int_le', [i1, v1], Bool)
    false_link, true_link = closeblock2(loopblock, v2)
    closereturnlink(false_link, result1)
    closelink(true_link, [result1, i1, v1], loopblock)
    
    res = runblock(block, [0])
    assert res == 1
    res = runblock(block, [1])
    assert res == 1
    res = runblock(block, [7])
    assert res == 5040
