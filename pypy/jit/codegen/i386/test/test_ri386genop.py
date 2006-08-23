from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.objectmodel import keepalive_until_here
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
    res = add_x(y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_adder_interpret():
    from pypy.rpython import rgenop
    gv_add_5 = make_adder(rgenop, 5)
    add_5 = rgenop.revealconst(lltype.Ptr(FUNC), gv_add_5)
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(add_5._obj.graph, [12])
    assert res == 17

def test_adder_direct():
    rgenop = RI386GenOp()
    gv_add_5 = make_adder(rgenop, 5)
    print gv_add_5.value
    fnptr = cast(c_void_p(gv_add_5.value), CFUNCTYPE(c_int, c_int))
    res = fnptr(37)    # <== the segfault is here
    assert res == 42

def test_adder_compile():
    fn = compile(runner, [int, int])
    res = fn(9080983, -9080941)
    assert res == 42

# ____________________________________________________________

FUNC2 = lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed)

def make_dummy(rgenop):
    # 'return x - (y - (x-1))'
    gv_SIGNED = rgenop.constTYPE(lltype.Signed)
    block = rgenop.newblock()
    gv_x = rgenop.geninputarg(block, gv_SIGNED)
    gv_y = rgenop.geninputarg(block, gv_SIGNED)
    args_gv = [gv_x, rgenop.genconst(1)]
    gv_z = rgenop.genop(block, "int_sub", args_gv, gv_SIGNED)
    link = rgenop.closeblock1(block)

    block2 = rgenop.newblock()
    gv_y2 = rgenop.geninputarg(block2, gv_SIGNED)
    gv_z2 = rgenop.geninputarg(block2, gv_SIGNED)
    gv_x2 = rgenop.geninputarg(block2, gv_SIGNED)
    rgenop.closelink(link, [gv_y, gv_z, gv_x], block2)

    args_gv = [gv_y2, gv_z2]
    gv_s2 = rgenop.genop(block2, "int_sub", args_gv, gv_SIGNED)
    args_gv = [gv_x2, gv_s2]
    gv_t2 = rgenop.genop(block2, "int_sub", args_gv, gv_SIGNED)
    link2 = rgenop.closeblock1(block2)

    rgenop.closereturnlink(link2, gv_t2)
    gv_FUNC2 = rgenop.constTYPE(FUNC2)
    gv_dummyfn = rgenop.gencallableconst("dummy", block, gv_FUNC2)
    return gv_dummyfn

def dummy_runner(x, y):
    rgenop = RI386GenOp()
    gv_dummyfn = make_dummy(rgenop)
    dummyfn = rgenop.revealconst(lltype.Ptr(FUNC2), gv_dummyfn)
    res = dummyfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_dummy_interpret():
    from pypy.rpython import rgenop
    gv_dummyfn = make_dummy(rgenop)
    dummyfn = rgenop.revealconst(lltype.Ptr(FUNC2), gv_dummyfn)
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(dummyfn._obj.graph, [30, 17])
    assert res == 42

def test_dummy_direct():
    rgenop = RI386GenOp()
    gv_dummyfn = make_dummy(rgenop)
    print gv_dummyfn.value
    fnptr = cast(c_void_p(gv_dummyfn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 17)    # <== the segfault is here
    assert res == 42

def test_dummy_compile():
    fn = compile(dummy_runner, [int, int])
    res = fn(40, 37)
    assert res == 42
