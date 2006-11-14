from pypy.rpython.annlowlevel import MixLevelAnnotatorPolicy
from pypy.rlib.objectmodel import keepalive_until_here
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
    args_gv = [gv_y]
    false_builder.enter_next_block([signed_kind], args_gv)
    [gv_y] = args_gv
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

# loop start block
def loop_start(rgenop, builder, signed_kind, gv_x, gv_y):
    args_gv = [gv_x, gv_y, rgenop.genconst(1)]
    loopblock = builder.enter_next_block(
        [signed_kind, signed_kind, signed_kind], args_gv)
    [gv_x, gv_y, gv_z] = args_gv

    gv_cond = builder.genop2("int_gt", gv_x, rgenop.genconst(0))
    bodybuilder = builder.jump_if_true(gv_cond)
    return args_gv, loopblock, bodybuilder

# loop exit
def loop_exit(builder, sigtoken, signed_kind, gv_y, gv_z):
    args_gv = [gv_y, gv_z]
    builder.enter_next_block(
        [signed_kind, signed_kind], args_gv)
    [gv_y, gv_z] = args_gv
    gv_y3 = builder.genop2("int_add", gv_y, gv_z)
    builder.finish_and_return(sigtoken, gv_y3)

# loop body
def loop_body(rgenop, loopblock, bodybuilder, signed_kind, gv_x, gv_y, gv_z):
    args_gv = [gv_z, gv_y, gv_x]
    bodybuilder.enter_next_block(
        [signed_kind, signed_kind, signed_kind], args_gv)
    [gv_z, gv_y, gv_x] = args_gv

    gv_z2 = bodybuilder.genop2("int_mul", gv_x, gv_z)
    gv_y2 = bodybuilder.genop2("int_add", gv_x, gv_y)
    gv_x2 = bodybuilder.genop2("int_sub", gv_x, rgenop.genconst(1))
    bodybuilder.finish_and_goto([gv_x2, gv_y2, gv_z2], loopblock)

def make_goto(rgenop):
    # z = 1
    # while x > 0:
    #     y += x
    #     z *= x
    #     x -= 1
    # y += z
    # return y
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x, gv_y] = rgenop.newgraph(sigtoken)

    [gv_x, gv_y, gv_z],loopblock,bodybuilder = loop_start(
        rgenop, builder, signed_kind, gv_x, gv_y)
    loop_exit(
        builder, sigtoken, signed_kind, gv_y, gv_z)
    loop_body(
        rgenop, loopblock, bodybuilder, signed_kind, gv_x, gv_y, gv_z)

    # done
    gv_gotofn = rgenop.gencallableconst(sigtoken, "goto", entrypoint)
    return gv_gotofn

def get_goto_runner(RGenOp):
    def goto_runner(x, y):
        rgenop = RGenOp()
        gv_gotofn = make_goto(rgenop)
        gotofn = gv_gotofn.revealconst(lltype.Ptr(FUNC2))
        res = gotofn(x, y)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return goto_runner

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

def get_if_runner(RGenOp):
    def if_runner(x, y):
        rgenop = RGenOp()
        gv_iffn = make_if(rgenop)
        iffn = gv_iffn.revealconst(lltype.Ptr(FUNC2))
        res = iffn(x, y)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return if_runner

def make_switch(rgenop):
    """
    def f(v0, v1):
        if v0 == 0: # switch
            return 21*v1
        elif v0 == 1:
            return 21+v1
        else:
            return v1
    """
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv0, gv1] = rgenop.newgraph(sigtoken)

    flexswitch = builder.flexswitch(gv0)
    const21 = rgenop.genconst(21)

    # case == 0
    const0 = rgenop.genconst(0)
    case_builder = flexswitch.add_case(const0)
    case_args_gv = [gv1]
    case_builder.enter_next_block([signed_kind], case_args_gv)
    [gv1_case0] = case_args_gv
    gv_res_case0 = case_builder.genop2('int_mul', const21, gv1_case0)
    case_builder.finish_and_return(sigtoken, gv_res_case0)
    # default
    default_builder = flexswitch.add_default()
    default_args_gv = [gv1]
    default_builder.enter_next_block([signed_kind], default_args_gv)
    [gv1_default] = default_args_gv
    default_builder.finish_and_return(sigtoken, gv1_default)
    # case == 1
    const1 = rgenop.genconst(1)
    case_builder = flexswitch.add_case(const1)
    case_args_gv = [gv1]
    case_builder.enter_next_block([signed_kind], case_args_gv)
    [gv1_case1] = case_args_gv
    gv_res_case1 = case_builder.genop2('int_add', const21, gv1_case1)
    case_builder.finish_and_return(sigtoken, gv_res_case1)

    gv_switch = rgenop.gencallableconst(sigtoken, "switch", entrypoint)
    return gv_switch

def get_switch_runner(RGenOp):
    def switch_runner(x, y):
        rgenop = RGenOp()
        gv_switchfn = make_switch(rgenop)
        switchfn = gv_switchfn.revealconst(lltype.Ptr(FUNC2))
        res = switchfn(x, y)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return switch_runner

def make_large_switch(rgenop):
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

def get_large_switch_runner(RGenOp):
    def large_switch_runner(x, y):
        rgenop = RGenOp()
        gv_large_switchfn = make_large_switch(rgenop)
        largeswitchfn = gv_large_switchfn.revealconst(lltype.Ptr(FUNC2))
        res = largeswitchfn(x, y)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return large_switch_runner

def make_fact(rgenop):
    # def fact(x):
    #     if x:
    #         y = x-1
    #         z = fact(y)
    #         w = x*z
    #         return w
    #     return 1
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC)
    builder, entrypoint, [gv_x] = rgenop.newgraph(sigtoken)

    gv_fact = rgenop.gencallableconst(sigtoken, "fact", entrypoint)

    gv_cond = builder.genop1("int_is_true", gv_x)

    true_builder = builder.jump_if_true(gv_cond)

    args_gv = [gv_x]
    true_builder.enter_next_block([signed_kind], args_gv)
    [gv_x2] = args_gv

    gv_y = true_builder.genop2("int_sub", gv_x, rgenop.genconst(1))
    gv_z = true_builder.genop_call(sigtoken, gv_fact, [gv_y])
    gv_w = true_builder.genop2("int_mul", gv_x, gv_z)

    true_builder.finish_and_return(sigtoken, gv_w)

    builder.enter_next_block([], [])

    builder.finish_and_return(sigtoken, rgenop.genconst(1))
    return gv_fact

def get_fact_runner(RGenOp):
    def fact_runner(x):
        rgenop = RGenOp()
        gv_large_switchfn = make_fact(rgenop)
        largeswitchfn = gv_large_switchfn.revealconst(lltype.Ptr(FUNC))
        res = largeswitchfn(x)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return fact_runner

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

    def test_goto_direct(self):
        rgenop = self.RGenOp()
        gv_gotofn = make_goto(rgenop)
        print gv_gotofn.value
        fnptr = cast(c_void_p(gv_gotofn.value), CFUNCTYPE(c_int, c_int, c_int))
        res = fnptr(10, 17)    # <== the segfault is here
        assert res == 3628872
        res = fnptr(3, 17)    # <== or here
        assert res == 29

    def test_goto_compile(self):
        fn = self.compile(get_goto_runner(self.RGenOp), [int, int])
        res = fn(10, 17)
        assert res == 3628872
        res = fn(3, 17)
        assert res == 29

    def test_if_direct(self):
        rgenop = self.RGenOp()
        gv_iffn = make_if(rgenop)
        print gv_iffn.value
        fnptr = cast(c_void_p(gv_iffn.value), CFUNCTYPE(c_int, c_int, c_int))
        res = fnptr(30, 0)
        assert res == 45
        res = fnptr(3, 0)
        assert res == 6

    def test_if_compile(self):
        fn = self.compile(get_if_runner(self.RGenOp), [int, int])
        res = fn(30, 0)
        assert res == 45
        res = fn(3, 0)
        assert res == 6

    def test_switch_direct(self):
        rgenop = self.RGenOp()
        gv_switchfn = make_switch(rgenop)
        print gv_switchfn.value
        import os
        fnptr = cast(c_void_p(gv_switchfn.value), CFUNCTYPE(c_int, c_int))
        res = fnptr(0, 2)
        assert res == 42
        res = fnptr(1, 16)
        assert res == 37
        res = fnptr(42, 16)
        assert res == 16

    def test_switch_compile(self):
        fn = self.compile(get_switch_runner(self.RGenOp), [int, int])
        res = fn(0, 2)
        assert res == 42
        res = fn(1, 17)
        assert res == 38
        res = fn(42, 18)
        assert res == 18

    def test_large_switch_direct(self):
        rgenop = self.RGenOp()
        gv_switchfn = make_large_switch(rgenop)
        print gv_switchfn.value
        fnptr = cast(c_void_p(gv_switchfn.value), CFUNCTYPE(c_int, c_int, c_int))
        res = fnptr(0, 2)
        assert res == 42
        for x in range(1,11):
            res = fnptr(x, 5)
            assert res == 2**x+5
        res = fnptr(42, 16)
        assert res == 16

    def test_large_switch_compile(self):
        fn = self.compile(get_large_switch_runner(self.RGenOp), [int, int])
        res = fn(0, 2)
        assert res == 42
        for x in range(1,11):
            res = fn(x, 7)
            assert res == 2**x+7 
        res = fn(42, 18)
        assert res == 18

    def test_fact_direct(self):
        rgenop = self.RGenOp()
        gv_fact = make_fact(rgenop)
        print gv_fact.value
        fnptr = cast(c_void_p(gv_fact.value), CFUNCTYPE(c_int))
        res = fnptr(2)
        assert res == 2
        res = fnptr(10)
        assert res == 3628800

    def test_fact_compile(self):
        fn = self.compile(get_fact_runner(self.RGenOp), [int])
        res = fn(2)
        assert res == 2
        res = fn(11)
        assert res == 39916800

