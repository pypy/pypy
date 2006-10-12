from pypy.jit.codegen.ppc.rppcgenop import RPPCGenOp
from ctypes import c_void_p, cast, CFUNCTYPE, c_int
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import keepalive_until_here
from pypy.rpython.annlowlevel import MixLevelAnnotatorPolicy
import py

# XXX clean up
class PseudoAnnhelper(object):
    rtyper = None
GENOP_POLICY = MixLevelAnnotatorPolicy(PseudoAnnhelper())

FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)

def compile(func, inputtypes):
    from pypy.translator.c.test.test_genc import compile
    return compile(func, inputtypes,
                   annotatorpolicy=GENOP_POLICY,
                   gcpolicy='boehm')

def make_adder(rgenop, n):
    # 'return x+n'
    sigtoken = rgenop.sigToken(FUNC)
    builder, entrypoint, [gv_x] = rgenop.newgraph(sigtoken)
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(n))
    builder.finish_and_return(sigtoken, gv_result)
    gv_add_one = rgenop.gencallableconst(sigtoken, "adder", entrypoint)
    return gv_add_one

def test_adder_direct():
    rgenop = RPPCGenOp()
    gv_add_5 = make_adder(rgenop, 5)
    print gv_add_5.value
    fnptr = cast(c_void_p(gv_add_5.value), CFUNCTYPE(c_int, c_int))
    res = fnptr(37)
    assert res == 42

def runner(x, y):
    rgenop = RPPCGenOp()
    gv_add_x = make_adder(rgenop, x)
    add_x = gv_add_x.revealconst(lltype.Ptr(FUNC))
    res = add_x(y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_adder_compile():
    fn = compile(runner, [int, int])
    res = fn(9080983, -9080941)
    assert res == 42

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

def dummy_runner(x, y):
    rgenop = RPPCGenOp()
    gv_dummyfn = make_dummy(rgenop)
    dummyfn = gv_dummyfn.revealconst(lltype.Ptr(FUNC2))
    res = dummyfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_dummy_direct():
    rgenop = RPPCGenOp()
    gv_dummyfn = make_dummy(rgenop)
    print gv_dummyfn.value
    fnptr = cast(c_void_p(gv_dummyfn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 17)    # <== the segfault is here
    assert res == 42

def test_dummy_compile():
    fn = compile(dummy_runner, [int, int])
    res = fn(40, 37)
    assert res == 42
