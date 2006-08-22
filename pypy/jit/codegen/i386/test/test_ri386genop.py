from pypy.rpython.lltypesystem import lltype
from pypy.rpython import llinterp
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy.jit.codegen.i386.ri386genop import RI386GenOp

from ctypes import c_void_p, cast, CFUNCTYPE, c_int

# ____________________________________________________________

FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)

def make_adder(rgenop, n):
    # 'return x+n'
    gv_SIGNED = rgenop.constTYPE(lltype.Signed)
    block = rgenop.newblock()
    gv_x = rgenop.geninputarg(block, gv_SIGNED)
    args_gv = [gv_x,
               rgenop.genconst(n)]
    gv_result = rgenop.genop(block, "int_add", args_gv, gv_SIGNED)
    link = rgenop.closeblock1(block)
    rgenop.closereturnlink(link, gv_result)

    gv_FUNC = rgenop.constTYPE(FUNC)
    gv_add_one = rgenop.gencallableconst("adder", block, gv_FUNC)
    return gv_add_one

def runner(x, y):
    rgenop = RI386GenOp()
    gv_add_x = make_adder(rgenop, x)
    add_x = rgenop.revealconst(lltype.Ptr(FUNC), gv_add_x)
    return add_x(y)

# ____________________________________________________________

def test_adder_direct():
    rgenop = RI386GenOp()
    gv_add_5 = make_adder(rgenop, 5)
    print gv_add_5.value
    fnptr = cast(c_void_p(gv_add_5.value), CFUNCTYPE(c_int, c_int))
    res = fnptr(37)    # <== the segfault is here
    assert res == 42

def test_adder_compile():
    import py; py.test.skip("in-progress")
    fn = compile(runner, [int, int])
    res = fn(9080983, -9080941)
    assert res == 42
