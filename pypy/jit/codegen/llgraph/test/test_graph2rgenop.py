from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.graph2rgenop import rcompile
from pypy.jit.codegen.llgraph.rgenop import rgenop
from pypy.jit.codegen.llgraph.llimpl import testgengraph


def demo(n):
    result = 1
    while n > 1:
        if n & 1:
            result *= n
        n -= 1
    return result


def test_demo():
    gv = rcompile(rgenop, demo, [int])
    F1 = lltype.FuncType([lltype.Signed], lltype.Signed)
    ptr = gv.revealconst(lltype.Ptr(F1))

    res = testgengraph(ptr._obj.graph, [10])
    assert res == demo(10) == 945
