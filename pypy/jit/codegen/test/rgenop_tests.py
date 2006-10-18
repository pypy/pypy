from pypy.rpython.annlowlevel import MixLevelAnnotatorPolicy
from pypy.rpython.objectmodel import keepalive_until_here
from pypy.rpython.lltypesystem import lltype
from pypy.translator.c.test import test_boehm
from ctypes import c_void_p, cast, CFUNCTYPE, c_int

class PseudoAnnhelper(object):
    rtyper = None
GENOP_POLICY = MixLevelAnnotatorPolicy(PseudoAnnhelper())

FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)

def make_adder(rgenop, n):
    # 'return x+n'
    sigtoken = rgenop.sigToken(FUNC)
    builder, entrypoint, [gv_x] = rgenop.newgraph(sigtoken)
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(n))
    builder.finish_and_return(sigtoken, gv_result)
    gv_add_one = rgenop.gencallableconst(sigtoken, "adder", entrypoint)
    return gv_add_one

def get_adder_runner(RGenOp):
    def runner(x, y):
        rgenop = RGenOp()
        gv_add_x = make_adder(rgenop, x)
        add_x = gv_add_x.revealconst(lltype.Ptr(FUNC))
        res = add_x(y)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return runner

class AbstractRGenOpTests(test_boehm.AbstractGCTestClass):
    RGenOp = None

    def compile(self, runner, argtypes):
        return self.getcompiled(runner, argtypes,
                                annotatorpolicy = GENOP_POLICY)

    def test_adder_direct(self):
        rgenop = self.RGenOp()
        gv_add_5 = make_adder(rgenop, 5)
        fnptr = cast(c_void_p(gv_add_5.value), CFUNCTYPE(c_int, c_int))
        res = fnptr(37)
        assert res == 42

    def test_adder_compile(self):
        fn = self.compile(get_adder_runner(self.RGenOp), [int, int])
        res = fn(9080983, -9080941)
        assert res == 42

