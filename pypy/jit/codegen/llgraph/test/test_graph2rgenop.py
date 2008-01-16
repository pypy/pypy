from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
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

class BaseTest:
    type_system = None
    FuncType = None
    Ptr = None

    def test_demo(self):
        gv = rcompile(rgenop, demo, [int], type_system=self.type_system)
        F1 = self.FuncType([lltype.Signed], lltype.Signed)
        func = gv.revealconst(self.Ptr(F1))

        res = testgengraph(self.deref(func).graph, [10])
        assert res == demo(10) == 945

class TestLLType(BaseTest):
    type_system = 'lltype'
    FuncType = lltype.FuncType
    Ptr = lltype.Ptr

    def deref(self, ptr):
        return ptr._obj

class TestOOType(BaseTest):
    type_system = 'ootype'
    FuncType = ootype.StaticMethod

    def Ptr(self, x):
        return x

    def deref(self, obj):
        return obj
