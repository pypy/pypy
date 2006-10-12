from pypy.jit.codegen.ppc.rppcgenop import RPPCGenOp
from ctypes import c_void_p, cast, CFUNCTYPE, c_int
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import keepalive_until_here
from pypy.rpython.annlowlevel import MixLevelAnnotatorPolicy
from pypy.translator.c.test.test_genc import compile

from ctypes import c_void_p, cast, CFUNCTYPE, c_int

# XXX clean up
class PseudoAnnhelper(object):
    rtyper = None
GENOP_POLICY = MixLevelAnnotatorPolicy(PseudoAnnhelper())
import py

FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)

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
    fn = compile(runner, [int, int], annotatorpolicy=GENOP_POLICY,
                 gcpolicy='boehm')
    res = fn(9080983, -9080941)
    assert res == 42
