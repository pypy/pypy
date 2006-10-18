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

FUNC2 = lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed)

def make_dummy(rgenop):
    # 'return x - (y - (x-1))'
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x, gv_y] = rgenop.newgraph(sigtoken)
    gv_z = builder.genop2("int_sub", gv_x, rgenop.genconst(1))

    args_gv = [gv_y, gv_z, gv_x]
    builder.enter_next_block([signed_kind, signed_kind, signed_kind], args_gv)
    [gv_y2, gv_z2, gv_x2] = args_gv

    gv_s2 = builder.genop2("int_sub", gv_y2, gv_z2)
    gv_t2 = builder.genop2("int_sub", gv_x2, gv_s2)
    builder.finish_and_return(sigtoken, gv_t2)

    gv_dummyfn = rgenop.gencallableconst(sigtoken, "dummy", entrypoint)
    return gv_dummyfn

def get_dummy_runner(RGenOp):
    def dummy_runner(x, y):
        rgenop = RGenOp()
        gv_dummyfn = make_dummy(rgenop)
        dummyfn = gv_dummyfn.revealconst(lltype.Ptr(FUNC2))
        res = dummyfn(x, y)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return dummy_runner

def make_branching(rgenop):
    # 'if x > 5: return x-1
    #  else:     return y'
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x, gv_y] = rgenop.newgraph(sigtoken)
    gv_cond = builder.genop2("int_gt", gv_x, rgenop.genconst(5))
    false_builder = builder.jump_if_false(gv_cond)

    # true path
    args_gv = [rgenop.genconst(1), gv_x, gv_y]
    builder.enter_next_block([signed_kind, signed_kind, signed_kind], args_gv)
    [gv_one, gv_x2, gv_y2] = args_gv

    gv_s2 = builder.genop2("int_sub", gv_x2, gv_one)
    builder.finish_and_return(sigtoken, gv_s2)

    # false path
    false_builder.finish_and_return(sigtoken, gv_y)

    # done
    gv_branchingfn = rgenop.gencallableconst(sigtoken,
                                             "branching", entrypoint)
    return gv_branchingfn

def get_branching_runner(RGenOp):
    def branching_runner(x, y):
        rgenop = RGenOp()
        gv_branchingfn = make_branching(rgenop)
        branchingfn = gv_branchingfn.revealconst(lltype.Ptr(FUNC2))
        res = branchingfn(x, y)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return branching_runner


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

    def test_dummy_direct(self):
        rgenop = self.RGenOp()
        gv_dummyfn = make_dummy(rgenop)
        print gv_dummyfn.value
        fnptr = cast(c_void_p(gv_dummyfn.value), CFUNCTYPE(c_int, c_int, c_int))
        res = fnptr(30, 17)
        assert res == 42

    def test_dummy_compile(self):
        fn = self.compile(get_dummy_runner(self.RGenOp), [int, int])
        res = fn(40, 37)
        assert res == 42

    def test_branching_direct(self):
        rgenop = self.RGenOp()
        gv_branchingfn = make_branching(rgenop)
        fnptr = cast(c_void_p(gv_branchingfn.value),
                     CFUNCTYPE(c_int, c_int, c_int))
        res = fnptr(30, 17)
        assert res == 29
        res = fnptr(3, 17)
        assert res == 17

    def test_branching_compile(self):
        fn = self.compile(get_branching_runner(self.RGenOp), [int, int])
        res = fn(30, 17)
        assert res == 29
        res = fn(3, 17)
        assert res == 17
