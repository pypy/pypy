from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.objectmodel import keepalive_until_here
from pypy.rpython.annlowlevel import MixLevelAnnotatorPolicy
from pypy.translator.c.test import test_boehm
from pypy.jit.codegen.i386.rgenop import RI386GenOp

from ctypes import c_void_p, cast, CFUNCTYPE, c_int

# ____________________________________________________________

FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)

def make_adder(rgenop, n):
    # 'return x+n'
    sigtoken = rgenop.sigToken(FUNC)
    builder, entrypoint, [gv_x] = rgenop.newgraph(sigtoken)
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(n))
    builder.finish_and_return(sigtoken, gv_result)
    gv_add_one = rgenop.gencallableconst(sigtoken, "adder", entrypoint)
    return gv_add_one

def runner(x, y):
    rgenop = RI386GenOp()
    gv_add_x = make_adder(rgenop, x)
    add_x = gv_add_x.revealconst(lltype.Ptr(FUNC))
    res = add_x(y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_adder_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_add_5 = make_adder(rgenop, 5)
    add_5 = gv_add_5.revealconst(lltype.Ptr(FUNC))
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


# ____________________________________________________________

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
    rgenop = RI386GenOp()
    gv_dummyfn = make_dummy(rgenop)
    dummyfn = gv_dummyfn.revealconst(lltype.Ptr(FUNC2))
    res = dummyfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_dummy_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_dummyfn = make_dummy(rgenop)
    dummyfn = gv_dummyfn.revealconst(lltype.Ptr(FUNC2))
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

# ____________________________________________________________

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

def branching_runner(x, y):
    rgenop = RI386GenOp()
    gv_branchingfn = make_branching(rgenop)
    branchingfn = gv_branchingfn.revealconst(lltype.Ptr(FUNC2))
    res = branchingfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_branching_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_branchingfn = make_branching(rgenop)
    branchingfn = gv_branchingfn.revealconst(lltype.Ptr(FUNC2))
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(branchingfn._obj.graph, [30, 17])
    assert res == 29
    res = llinterp.eval_graph(branchingfn._obj.graph, [3, 17])
    assert res == 17

def test_branching_direct():
    rgenop = RI386GenOp()
    gv_branchingfn = make_branching(rgenop)
    print gv_branchingfn.value
    fnptr = cast(c_void_p(gv_branchingfn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 17)    # <== the segfault is here
    assert res == 29
    res = fnptr(3, 17)    # <== or here
    assert res == 17

# ____________________________________________________________

def make_goto(rgenop):
    # while x > 0:
    #     y += x
    #     x -= 1
    # return y
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x, gv_y] = rgenop.newgraph(sigtoken)

    # loop start block
    args_gv = [gv_x, gv_y]
    loopblock = builder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_x, gv_y] = args_gv

    gv_cond = builder.genop2("int_gt", gv_x, rgenop.genconst(0))
    bodybuilder = builder.jump_if_true(gv_cond)
    builder.finish_and_return(sigtoken, gv_y)

    # loop body
    args_gv = [gv_y, gv_x]
    bodybuilder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_y, gv_x] = args_gv

    gv_y2 = bodybuilder.genop2("int_add", gv_x, gv_y)
    gv_x2 = bodybuilder.genop2("int_sub", gv_x, rgenop.genconst(1))
    bodybuilder.finish_and_goto([gv_x2, gv_y2], loopblock)

    # done
    gv_gotofn = rgenop.gencallableconst(sigtoken, "goto", entrypoint)
    return gv_gotofn

def goto_runner(x, y):
    rgenop = RI386GenOp()
    gv_gotofn = make_goto(rgenop)
    gotofn = gv_gotofn.revealconst(lltype.Ptr(FUNC2))
    res = gotofn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_goto_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_gotofn = make_goto(rgenop)
    gotofn = gv_gotofn.revealconst(lltype.Ptr(FUNC2))
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(gotofn._obj.graph, [30, 17])
    assert res == 31 * 15 + 17
    res = llinterp.eval_graph(gotofn._obj.graph, [3, 17])
    assert res == 23

def test_goto_direct():
    rgenop = RI386GenOp()
    gv_gotofn = make_goto(rgenop)
    print gv_gotofn.value
    fnptr = cast(c_void_p(gv_gotofn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 17)    # <== the segfault is here
    assert res == 31 * 15 + 17
    res = fnptr(3, 17)    # <== or here
    assert res == 23

# ____________________________________________________________

def make_if(rgenop):
    # a = x
    # if x > 5:
    #     x //= 2
    # return x + a
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x1, gv_unused] = rgenop.newgraph(sigtoken)

    # check
    args_gv = [gv_x1, gv_unused]
    builder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_x1, gv_unused] = args_gv

    gv_cond = builder.genop2("int_gt", gv_x1, rgenop.genconst(5))
    elsebuilder = builder.jump_if_false(gv_cond)
    elseargs_gv = [gv_x1]

    # 'then' block
    args_gv = [gv_x1]
    builder.enter_next_block([signed_kind], args_gv)
    [gv_x1] = args_gv
    gv_x2 = builder.genop2("int_floordiv", gv_x1, rgenop.genconst(2))

    # end block
    args_gv = [gv_x2, gv_x1]
    label = builder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_x2, gv_a] = args_gv
    gv_res = builder.genop2("int_add", gv_x2, gv_a)
    builder.finish_and_return(sigtoken, gv_res)

    # now the else branch
    elsebuilder.enter_next_block([signed_kind], elseargs_gv)
    [gv_x3] = elseargs_gv
    elsebuilder.finish_and_goto([gv_x3, gv_x3], label)

    # done
    gv_gotofn = rgenop.gencallableconst(sigtoken, "goto", entrypoint)
    return gv_gotofn

def if_runner(x, y):
    rgenop = RI386GenOp()
    gv_iffn = make_if(rgenop)
    iffn = gv_iffn.revealconst(lltype.Ptr(FUNC2))
    res = iffn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_if_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_iffn = make_if(rgenop)
    iffn = gv_iffn.revealconst(lltype.Ptr(FUNC2))
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(iffn._obj.graph, [30, 0])
    assert res == 45
    res = llinterp.eval_graph(iffn._obj.graph, [3, 0])
    assert res == 6

def test_if_direct():
    rgenop = RI386GenOp()
    gv_iffn = make_if(rgenop)
    print gv_iffn.value
    fnptr = cast(c_void_p(gv_iffn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 0)
    assert res == 45
    res = fnptr(3, 0)
    assert res == 6

# ____________________________________________________________

def build_switch(rgenop):
    """
    def f(v0, v1):
        if v0 == 0: # switch
            return 21*v1
        elif v0 == 1:
            return 21+v1
        else:
            return v1
    """
    signed_tok = rgenop.kindToken(lltype.Signed)
    f2_token = rgenop.sigToken(FUNC2)
    builder, graph, (gv0, gv1) = rgenop.newgraph(f2_token)

    flexswitch = builder.flexswitch(gv0)
    const21 = rgenop.genconst(21)

    # case == 0
    const0 = rgenop.genconst(0)
    case_builder = flexswitch.add_case(const0)
    case_args_gv = [gv1]
    case_builder.enter_next_block([signed_tok], case_args_gv)
    [gv1_case0] = case_args_gv
    gv_res_case0 = case_builder.genop2('int_mul', const21, gv1_case0)
    case_builder.finish_and_return(f2_token, gv_res_case0)
    # default
    default_builder = flexswitch.add_default()
    default_args_gv = [gv1]
    default_builder.enter_next_block([signed_tok], default_args_gv)
    [gv1_default] = default_args_gv
    default_builder.finish_and_return(f2_token, gv1_default)
    # case == 1
    const1 = rgenop.genconst(1)
    case_builder = flexswitch.add_case(const1)
    case_args_gv = [gv1]
    case_builder.enter_next_block([signed_tok], case_args_gv)
    [gv1_case1] = case_args_gv
    gv_res_case1 = case_builder.genop2('int_add', const21, gv1_case1)
    case_builder.finish_and_return(f2_token, gv_res_case1)

    gv_switch = rgenop.gencallableconst(f2_token, "switch", graph)
    return gv_switch

def switch_runner(x, y):
    rgenop = RI386GenOp()
    gv_switchfn = build_switch(rgenop)
    switchfn = gv_switchfn.revealconst(lltype.Ptr(FUNC2))
    res = switchfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_switch_direct():
    rgenop = RI386GenOp()
    gv_switchfn = build_switch(rgenop)
    print gv_switchfn.value
    fnptr = cast(c_void_p(gv_switchfn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(0, 2)
    assert res == 42
    res = fnptr(1, 16)
    assert res == 37
    res = fnptr(42, 16)
    assert res == 16

def build_large_switch(rgenop):
    """
    def f(v0, v1):
        if v0 == 0: # switch
            return 21*v1
        elif v0 == 1:
            return 2+v1
        elif v0 == 2:
            return 4+v1
        ...
        elif v0 == 10:
            return 2**10+v1
        else:
            return v1
    """
    signed_tok = rgenop.kindToken(lltype.Signed)
    f2_token = rgenop.sigToken(FUNC2)
    builder, graph, (gv0, gv1) = rgenop.newgraph(f2_token)

    flexswitch = builder.flexswitch(gv0)
    const21 = rgenop.genconst(21)

    # case == 0
    const0 = rgenop.genconst(0)
    case_builder = flexswitch.add_case(const0)
    case_args_gv = [gv1]
    case_builder.enter_next_block([signed_tok], case_args_gv)
    [gv1_case0] = case_args_gv
    gv_res_case0 = case_builder.genop2('int_mul', const21, gv1_case0)
    case_builder.finish_and_return(f2_token, gv_res_case0)
    # default
    default_builder = flexswitch.add_default()
    default_args_gv = [gv1]
    default_builder.enter_next_block([signed_tok], default_args_gv)
    [gv1_default] = default_args_gv
    default_builder.finish_and_return(f2_token, gv1_default)
    # case == x
    for x in range(1,11):
         constx = rgenop.genconst(x)
         case_builder = flexswitch.add_case(constx)
         case_args_gv = [gv1]
         case_builder.enter_next_block([signed_tok], case_args_gv)
         [gv1_casex] = case_args_gv
         const2px= rgenop.genconst(1<<x)
         gv_res_casex = case_builder.genop2('int_add', const2px, gv1_casex)
         case_builder.finish_and_return(f2_token, gv_res_casex)

    gv_switch = rgenop.gencallableconst(f2_token, "large_switch", graph)
    return gv_switch

def large_switch_runner(x, y):
    rgenop = RI386GenOp()
    gv_switchfn = build_large_switch(rgenop)
    switchfn = gv_switchfn.revealconst(lltype.Ptr(FUNC2))
    res = switchfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_large_switch_direct():
    rgenop = RI386GenOp()
    gv_switchfn = build_large_switch(rgenop)
    print gv_switchfn.value
    fnptr = cast(c_void_p(gv_switchfn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(0, 2)
    assert res == 42
    for x in range(1,11):
        res = fnptr(x, 5)
        assert res == 2**x+5 
    res = fnptr(42, 16)
    assert res == 16

# ____________________________________________________________

# XXX clean up
class PseudoAnnhelper(object):
    rtyper = None
GENOP_POLICY = MixLevelAnnotatorPolicy(PseudoAnnhelper())

class TestCompile(test_boehm.AbstractTestBoehmClass):

    def compile(self, runner, argtypes):
        return self.getcompiled(runner, argtypes,
                                annotatorpolicy = GENOP_POLICY)

    def test_adder_compile(self):
        fn = self.compile(runner, [int, int])
        res = fn(9080983, -9080941)
        assert res == 42


    def test_dummy_compile(self):
        fn = self.compile(dummy_runner, [int, int])
        res = fn(40, 37)
        assert res == 42

    def test_branching_compile(self):
        fn = self.compile(branching_runner, [int, int])
        res = fn(30, 17)
        assert res == 29
        res = fn(3, 17)
        assert res == 17

    def test_goto_compile(self):
        fn = self.compile(goto_runner, [int, int])
        res = fn(30, 17)
        assert res == 31 * 15 + 17
        res = fn(3, 17)
        assert res == 23

    def test_if_compile(self):
        fn = self.compile(if_runner, [int, int])
        res = fn(30, 0)
        assert res == 45
        res = fn(3, 0)
        assert res == 6

    def test_switch_compile(self):
        fn = self.compile(switch_runner, [int, int])
        res = fn(0, 2)
        assert res == 42
        res = fn(1, 17)
        assert res == 38
        res = fn(42, 18)
        assert res == 18

    def test_large_switch_compile(self):
        fn = self.compile(large_switch_runner, [int, int])
        res = fn(0, 2)
        assert res == 42
        for x in range(1,11):
            res = fn(x, 7)
            assert res == 2**x+7 
        res = fn(42, 18)
        assert res == 18

