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
    builder, gv_add_one, [gv_x] = rgenop.newgraph(sigtoken, "adder")
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(n))
    builder.finish_and_return(sigtoken, gv_result)
    builder.end()
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
    builder, gv_dummyfn, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "dummy")
    gv_z = builder.genop2("int_sub", gv_x, rgenop.genconst(1))

    args_gv = [gv_y, gv_z, gv_x]
    builder.enter_next_block([signed_kind, signed_kind, signed_kind], args_gv)
    [gv_y2, gv_z2, gv_x2] = args_gv

    gv_s2 = builder.genop2("int_sub", gv_y2, gv_z2)
    gv_t2 = builder.genop2("int_sub", gv_x2, gv_s2)
    builder.finish_and_return(sigtoken, gv_t2)

    builder.end()
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
    builder, gv_branchingfn, [gv_x, gv_y] = rgenop.newgraph(sigtoken,
                                                            "branching")
    gv_cond = builder.genop2("int_gt", gv_x, rgenop.genconst(5))
    false_builder = builder.jump_if_false(gv_cond, [gv_y])

    # true path
    args_gv = [rgenop.genconst(1), gv_x, gv_y]
    builder.enter_next_block([signed_kind, signed_kind, signed_kind], args_gv)
    [gv_one, gv_x2, gv_y2] = args_gv

    gv_s2 = builder.genop2("int_sub", gv_x2, gv_one)
    builder.finish_and_return(sigtoken, gv_s2)

    # false path
    false_builder.start_writing()
    false_builder.finish_and_return(sigtoken, gv_y)

    # done
    builder.end()
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
    bodybuilder = builder.jump_if_true(gv_cond, args_gv)
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
    bodybuilder.start_writing()
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
    builder, gv_gotofn, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "goto")

    [gv_x, gv_y, gv_z],loopblock,bodybuilder = loop_start(
        rgenop, builder, signed_kind, gv_x, gv_y)
    loop_exit(
        builder, sigtoken, signed_kind, gv_y, gv_z)
    loop_body(
        rgenop, loopblock, bodybuilder, signed_kind, gv_x, gv_y, gv_z)

    # done
    builder.end()
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
    builder, gv_gotofn, [gv_x1, gv_unused] = rgenop.newgraph(sigtoken, "if")

    # check
    args_gv = [gv_x1, gv_unused]
    builder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_x1, gv_unused] = args_gv

    gv_cond = builder.genop2("int_gt", gv_x1, rgenop.genconst(5))
    elsebuilder = builder.jump_if_false(gv_cond, [gv_x1])

    # 'then' block
    gv_x2 = builder.genop2("int_floordiv", gv_x1, rgenop.genconst(2))

    # end block
    args_gv = [gv_x2, gv_x1]
    label = builder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_x2, gv_a] = args_gv
    gv_res = builder.genop2("int_add", gv_x2, gv_a)
    builder.finish_and_return(sigtoken, gv_res)

    # now the else branch
    elsebuilder.start_writing()
    elsebuilder.finish_and_goto([gv_x1, gv_x1], label)

    # done
    builder.end()
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
    builder, gv_switch, [gv0, gv1] = rgenop.newgraph(sigtoken, "switch")

    flexswitch, default_builder = builder.flexswitch(gv0, [gv1])
    const21 = rgenop.genconst(21)

    # default
    default_builder.finish_and_return(sigtoken, gv1)
    # case == 0
    const0 = rgenop.genconst(0)
    case_builder = flexswitch.add_case(const0)
    gv_res_case0 = case_builder.genop2('int_mul', const21, gv1)
    case_builder.finish_and_return(sigtoken, gv_res_case0)
    # case == 1
    const1 = rgenop.genconst(1)
    case_builder = flexswitch.add_case(const1)
    gv_res_case1 = case_builder.genop2('int_add', const21, gv1)
    case_builder.finish_and_return(sigtoken, gv_res_case1)

    builder.end()
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
    builder, gv_switch, (gv0, gv1) = rgenop.newgraph(f2_token, "large_switch")

    flexswitch, default_builder = builder.flexswitch(gv0, [gv1])
    const21 = rgenop.genconst(21)

    # default
    default_builder.finish_and_return(f2_token, gv1)
    # case == 0
    const0 = rgenop.genconst(0)
    case_builder = flexswitch.add_case(const0)
    gv_res_case0 = case_builder.genop2('int_mul', const21, gv1)
    case_builder.finish_and_return(f2_token, gv_res_case0)
    # case == x
    for x in range(1,11):
         constx = rgenop.genconst(x)
         case_builder = flexswitch.add_case(constx)
         const2px = rgenop.genconst(1<<x)
         gv_res_casex = case_builder.genop2('int_add', const2px, gv1)
         case_builder.finish_and_return(f2_token, gv_res_casex)

    builder.end()
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
    builder, gv_fact, [gv_x] = rgenop.newgraph(sigtoken, "fact")

    gv_cond = builder.genop1("int_is_true", gv_x)

    true_builder = builder.jump_if_true(gv_cond, [gv_x])

    builder.enter_next_block([], [])
    builder.finish_and_return(sigtoken, rgenop.genconst(1))

    true_builder.start_writing()
    gv_y = true_builder.genop2("int_sub", gv_x, rgenop.genconst(1))
    gv_z = true_builder.genop_call(sigtoken, gv_fact, [gv_y])
    gv_w = true_builder.genop2("int_mul", gv_x, gv_z)
    true_builder.finish_and_return(sigtoken, gv_w)

    builder.end()
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

def make_func_calling_pause(rgenop):
    # def f(x):
    #     if x > 0:
    #          return x
    #     else:
    #          return -x
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC)
    builder, gv_f, [gv_x] = rgenop.newgraph(sigtoken, "abs")

    gv_cond = builder.genop2("int_gt", gv_x, rgenop.genconst(0))

    targetbuilder = builder.jump_if_false(gv_cond, [gv_x])

    builder = builder.pause_writing([gv_x])

    targetbuilder.start_writing()
    gv_negated = targetbuilder.genop1("int_neg", gv_x)
    targetbuilder.finish_and_return(sigtoken, gv_negated)

    builder.start_writing()
    builder.finish_and_return(sigtoken, gv_x)

    builder.end()
    return gv_f

def get_func_calling_pause_runner(RGenOp):
    def runner(x):
        rgenop = RGenOp()
        gv_abs = make_func_calling_pause(rgenop)
        myabs = gv_abs.revealconst(lltype.Ptr(FUNC))
        res = myabs(x)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return runner

def make_longwinded_and(rgenop):
    # def f(y): return 2 <= y <= 4
    # but more like this:
    # def f(y)
    #     x = 2 <= y
    #     if x:
    #         x = y <= 4
    #     if x:
    #        return 1
    #     else:
    #        return 0

    bool_kind = rgenop.kindToken(lltype.Bool)
    sigtoken = rgenop.sigToken(FUNC)
    builder, gv_f, [gv_y] = rgenop.newgraph(sigtoken, "abs")

    gv_x = builder.genop2("int_le", rgenop.genconst(2), gv_y)

    false_builder = builder.jump_if_false(gv_x, [gv_x])

    gv_x2 = builder.genop2("int_le", gv_y, rgenop.genconst(4))

    args_gv = [gv_x2]
    label = builder.enter_next_block([bool_kind], args_gv)
    [gv_x2] = args_gv

    return_false_builder = builder.jump_if_false(gv_x2, [])

    builder.finish_and_return(sigtoken, rgenop.genconst(1))

    false_builder.start_writing()
    false_builder.finish_and_goto([gv_x], label)

    return_false_builder.start_writing()
    return_false_builder.finish_and_return(sigtoken, rgenop.genconst(0))

    builder.end()
    return gv_f

def make_condition_result_cross_link(rgenop):

    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC)
    builder, gv_f, [gv_y] = rgenop.newgraph(sigtoken, "foo")

    gv_result = builder.genop2("int_eq", gv_y, rgenop.genconst(0))
    target1 = builder.jump_if_false(gv_result, [gv_result])

    builder.finish_and_return(sigtoken, rgenop.genconst(1))

    target1.start_writing()
    target2 = target1.jump_if_false(gv_result, [])

    # this return should be unreachable:
    target1.finish_and_return(sigtoken, rgenop.genconst(2))

    target2.start_writing()
    target2.finish_and_return(sigtoken, rgenop.genconst(3))

    builder.end()
    return gv_f

class AbstractRGenOpTests(test_boehm.AbstractGCTestClass):
    RGenOp = None

    def compile(self, runner, argtypes):
        return self.getcompiled(runner, argtypes,
                                annotatorpolicy = GENOP_POLICY)

    def cast(self, gv, nb_args):
        print gv.value
        return cast(c_void_p(gv.value), CFUNCTYPE(c_int, *[c_int]*nb_args))

    def test_adder_direct(self):
        rgenop = self.RGenOp()
        gv_add_5 = make_adder(rgenop, 5)
        fnptr = self.cast(gv_add_5, 1)
        res = fnptr(37)
        assert res == 42

    def test_adder_compile(self):
        fn = self.compile(get_adder_runner(self.RGenOp), [int, int])
        res = fn(9080983, -9080941)
        assert res == 42

    def test_dummy_direct(self):
        rgenop = self.RGenOp()
        gv_dummyfn = make_dummy(rgenop)
        fnptr = self.cast(gv_dummyfn, 2)
        res = fnptr(30, 17)
        assert res == 42

    def test_dummy_compile(self):
        fn = self.compile(get_dummy_runner(self.RGenOp), [int, int])
        res = fn(40, 37)
        assert res == 42

    def test_hide_and_reveal(self):
        RGenOp = self.RGenOp
        def hide_and_reveal(v):
            rgenop = RGenOp()
            gv = rgenop.genconst(v)
            res = gv.revealconst(lltype.Signed)
            keepalive_until_here(rgenop)
            return res
        res = hide_and_reveal(42)
        assert res == 42
        fn = self.compile(hide_and_reveal, [int])
        res = fn(42)
        assert res == 42

    def test_hide_and_reveal_p(self):
        RGenOp = self.RGenOp
        S = lltype.GcStruct('s', ('x', lltype.Signed))
        S_PTR = lltype.Ptr(S)
        s1 = lltype.malloc(S)
        s1.x = 8111
        s2 = lltype.malloc(S)
        s2.x = 8222
        def hide_and_reveal_p(n):
            rgenop = RGenOp()
            if n == 1:
                s = s1
            else:
                s = s2
            gv = rgenop.genconst(s)
            s_res = gv.revealconst(S_PTR)
            keepalive_until_here(rgenop)
            return s_res.x
        res = hide_and_reveal_p(1)
        assert res == 8111
        res = hide_and_reveal_p(2)
        assert res == 8222
        fn = self.compile(hide_and_reveal_p, [int])
        res = fn(1)
        assert res == 8111
        res = fn(2)
        assert res == 8222

    def test_branching_direct(self):
        rgenop = self.RGenOp()
        gv_branchingfn = make_branching(rgenop)
        fnptr = self.cast(gv_branchingfn, 2)
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
        fnptr = self.cast(gv_gotofn, 2)
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
        fnptr = self.cast(gv_iffn, 2)
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
        fnptr = self.cast(gv_switchfn, 2)
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
        fnptr = self.cast(gv_switchfn, 2)
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
        fnptr = self.cast(gv_fact, 1)
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

    def test_calling_pause_direct(self):
        rgenop = self.RGenOp()
        gv_abs = make_func_calling_pause(rgenop)
        fnptr = self.cast(gv_abs, 1)
        res = fnptr(2)
        assert res == 2
        res = fnptr(-42)
        assert res == 42

    def test_calling_pause_compile(self):
        fn = self.compile(get_func_calling_pause_runner(self.RGenOp), [int])
        res = fn(2)
        assert res == 2
        res = fn(-72)
        assert res == 72

    def test_longwinded_and_direct(self):
        rgenop = self.RGenOp()
        gv_fn = make_longwinded_and(rgenop)
        fnptr = self.cast(gv_fn, 1)

        res = fnptr(1)
        assert res == 0

        res = fnptr(2)
        assert res == 1

        res = fnptr(3)
        assert res == 1

        res = fnptr(4)
        assert res == 1

        res = fnptr(5)
        assert res == 0

    def test_condition_result_cross_link_direct(self):
        rgenop = self.RGenOp()
        gv_fn = make_condition_result_cross_link(rgenop)
        fnptr = self.cast(gv_fn, 1)

        res = fnptr(-1)
        assert res == 3

        res = fnptr(0)
        assert res == 1

        res = fnptr(1)
        assert res == 3


    def test_multiple_cmps(self):
        # return x>y + 10*x<y + 100*x<=y + 1000*x>=y + 10000*x==y + 100000*x!=y
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC2)
        builder, gv_callable, [gv_x, gv_y] = rgenop.newgraph(sigtoken,
                                                             "multicmp")

        args_gv = [gv_x, gv_y]
        builder.enter_next_block([signed_kind, signed_kind], args_gv)
        [gv_x, gv_y] = args_gv

        gv_gt = builder.genop2("int_gt", gv_x, gv_y)
        gv_lt = builder.genop2("int_lt", gv_x, gv_y)
        gv_ge = builder.genop2("int_ge", gv_x, gv_y)
        gv_le = builder.genop2("int_le", gv_x, gv_y)
        gv_eq = builder.genop2("int_eq", gv_x, gv_y)
        gv_ne = builder.genop2("int_ne", gv_x, gv_y)

        gv_gt1 = builder.genop1("cast_bool_to_int", gv_gt)
        gv_lt1 = builder.genop1("cast_bool_to_int", gv_lt)
        gv_ge1 = builder.genop1("cast_bool_to_int", gv_ge)
        gv_le1 = builder.genop1("cast_bool_to_int", gv_le)
        gv_eq1 = builder.genop1("cast_bool_to_int", gv_eq)
        gv_ne1 = builder.genop1("cast_bool_to_int", gv_ne)

        gv_gt2 = gv_gt1
        gv_lt2 = builder.genop2("int_mul", rgenop.genconst(10), gv_lt1)
        gv_ge2 = builder.genop2("int_mul", rgenop.genconst(100), gv_ge1)
        gv_le2 = builder.genop2("int_mul", rgenop.genconst(1000), gv_le1)
        gv_eq2 = builder.genop2("int_mul", rgenop.genconst(10000), gv_eq1)
        gv_ne2 = builder.genop2("int_mul", rgenop.genconst(100000), gv_ne1)

        gv_r0 = gv_gt2
        gv_r1 = builder.genop2("int_add", gv_r0, gv_lt2)
        gv_r2 = builder.genop2("int_add", gv_r1, gv_ge2)
        gv_r3 = builder.genop2("int_add", gv_r2, gv_le2)
        gv_r4 = builder.genop2("int_add", gv_r3, gv_eq2)
        gv_r5 = builder.genop2("int_add", gv_r4, gv_ne2)

        builder.finish_and_return(sigtoken, gv_r5)
        builder.end()
        fnptr = self.cast(gv_callable, 2)
        res = fnptr(1, 2)
        assert res == 101010
        res = fnptr(1, 1)
        assert res ==  11100
        res = fnptr(2, 1)
        assert res == 100101

    def test_flipped_cmp_with_immediate(self):
        # return
        # 1>x + 10*(1<x) + 100*(1>=x) + 1000*(1<=x) + 10000*(1==x) + 100000*(1!=x)
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken,
                                                       "multicmp")
        gv_one = rgenop.genconst(1)

        gv_gt = builder.genop2("int_gt", gv_one, gv_x)
        gv_lt = builder.genop2("int_lt", gv_one, gv_x)
        gv_ge = builder.genop2("int_ge", gv_one, gv_x)
        gv_le = builder.genop2("int_le", gv_one, gv_x)
        gv_eq = builder.genop2("int_eq", gv_one, gv_x)
        gv_ne = builder.genop2("int_ne", gv_one, gv_x)

        gv_gt1 = builder.genop1("cast_bool_to_int", gv_gt)
        gv_lt1 = builder.genop1("cast_bool_to_int", gv_lt)
        gv_ge1 = builder.genop1("cast_bool_to_int", gv_ge)
        gv_le1 = builder.genop1("cast_bool_to_int", gv_le)
        gv_eq1 = builder.genop1("cast_bool_to_int", gv_eq)
        gv_ne1 = builder.genop1("cast_bool_to_int", gv_ne)

        gv_gt2 = gv_gt1
        gv_lt2 = builder.genop2("int_mul", rgenop.genconst(10), gv_lt1)
        gv_ge2 = builder.genop2("int_mul", rgenop.genconst(100), gv_ge1)
        gv_le2 = builder.genop2("int_mul", rgenop.genconst(1000), gv_le1)
        gv_eq2 = builder.genop2("int_mul", rgenop.genconst(10000), gv_eq1)
        gv_ne2 = builder.genop2("int_mul", rgenop.genconst(100000), gv_ne1)

        gv_r0 = gv_gt2
        gv_r1 = builder.genop2("int_add", gv_r0, gv_lt2)
        gv_r2 = builder.genop2("int_add", gv_r1, gv_ge2)
        gv_r3 = builder.genop2("int_add", gv_r2, gv_le2)
        gv_r4 = builder.genop2("int_add", gv_r3, gv_eq2)
        gv_r5 = builder.genop2("int_add", gv_r4, gv_ne2)

        builder.finish_and_return(sigtoken, gv_r5)
        builder.end()
        fnptr = self.cast(gv_callable, 1)

        res = fnptr(0)
        assert res == 100101

        res = fnptr(1)
        assert res ==  11100

        res = fnptr(2)
        assert res == 101010

    def test_tight_loop(self):
        # while 1:
        #    y = x - 7
        #    if y < 0: break
        #    x = y
        # return x
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken,
                                                       "tightloop")
        args_gv = [gv_x]
        loopstart = builder.enter_next_block([signed_kind], args_gv)
        [gv_x] = args_gv

        gv_y = builder.genop2("int_sub", gv_x, rgenop.genconst(7))
        gv_cond = builder.genop2("int_lt", gv_y, rgenop.genconst(0))
        end_builder = builder.jump_if_true(gv_cond, [gv_x])
        builder.finish_and_goto([gv_y], loopstart)

        end_builder.start_writing()
        end_builder.finish_and_return(sigtoken, gv_x)
        builder.end()
        fnptr = self.cast(gv_callable, 1)

        res = fnptr(5)
        assert res == 5

        res = fnptr(44)
        assert res ==  2

    def test_jump_to_block_with_many_vars(self):
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_verysmall_callable, [gv_x] = rgenop.newgraph(sigtoken,
                                                                 "verysmall")
        builder.finish_and_return(sigtoken, rgenop.genconst(17))
        builder.end()

        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken,
                                                       "jtbwmv")
        gv_cond = builder.genop1("int_is_true", gv_x)
        builder2 = builder.jump_if_false(gv_cond, [gv_x])
        builder = builder.pause_writing([gv_x])

        builder2.start_writing()
        args_gv = [gv_x]
        label = builder2.enter_next_block([signed_kind], args_gv)
        [gv_x2] = args_gv

        gvs = []
        for i in range(50):
            gvs.append(builder2.genop2("int_mul", gv_x2, rgenop.genconst(i)))

        gvs.append(builder2.genop_call(sigtoken, gv_verysmall_callable,
                                       [gv_x2]))

        while len(gvs) > 1:
            gvs.append(builder2.genop2("int_add", gvs.pop(), gvs.pop()))

        builder2.finish_and_return(sigtoken, gvs.pop())

        builder.start_writing()
        builder.finish_and_goto([gv_x], label)
        builder.end()
        fnptr = self.cast(gv_callable, 1)

        res = fnptr(1291)
        assert res == 1291 * (49*50/2) + 17
