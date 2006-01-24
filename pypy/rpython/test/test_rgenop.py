from pypy.rpython.rgenop import *
from pypy.rpython.lltypesystem.lltype import *


def test_square():
    startlink = newgraph("square")
    block = newblock()
    v0 = geninputarg(block, Signed)
    v1 = genop(block, 'int_mul', [v0, v0], Signed)
    link = newreturnlink(block, v1)
    closeblock1(block, link)
    closelink(startlink, block)

    res = runlink(startlink, [17])
    assert res == 289
