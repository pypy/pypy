import random
from pypy.rpython.annlowlevel import MixLevelAnnotatorPolicy, llhelper
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.translator.c.test import test_boehm
from ctypes import c_void_p, cast, CFUNCTYPE, c_int

class PseudoAnnhelper(object):
    rtyper = None
GENOP_POLICY = MixLevelAnnotatorPolicy(PseudoAnnhelper())

FUNC  = lltype.FuncType([lltype.Signed], lltype.Signed)
FUNC2 = lltype.FuncType([lltype.Signed]*2, lltype.Signed)
FUNC3 = lltype.FuncType([lltype.Signed]*3, lltype.Signed)

def make_adder(rgenop, n):
    # 'return x+n'
    sigtoken = rgenop.sigToken(FUNC)
    builder, gv_add_one, [gv_x] = rgenop.newgraph(sigtoken, "adder")
    builder.start_writing()
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

def make_dummy(rgenop):
    # 'return x - (y - (x-1))'
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, gv_dummyfn, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "dummy")
    builder.start_writing()
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

FUNC100 = lltype.FuncType([lltype.Signed]*100, lltype.Signed)

def largedummy_example():
    args = [random.randrange(-10, 50) for i in range(100)]
    total = 0
    for i in range(0, 100, 2):
        total += args[i] - args[i+1]
    return args, total

def make_largedummy(rgenop):
    # 'return v0-v1+v2-v3+v4-v5...+v98-v99'
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC100)
    builder, gv_largedummyfn, gvs = rgenop.newgraph(sigtoken, "largedummy")
    builder.start_writing()

    for i in range(0, 100, 2):
        gvs.append(builder.genop2("int_sub", gvs[i], gvs[i+1]))

    builder.enter_next_block([signed_kind] * 150, gvs)
    while len(gvs) > 101:
        gv_sum = builder.genop2("int_add", gvs.pop(), gvs.pop())
        gvs.append(gv_sum)

    builder.finish_and_return(sigtoken, gvs.pop())

    builder.end()
    return gv_largedummyfn

def get_largedummy_runner(RGenOp):
    def largedummy_runner(v0,  v1,  v2,  v3,  v4,  v5,  v6,  v7,  v8,  v9,
                          v10, v11, v12, v13, v14, v15, v16, v17, v18, v19,
                          v20, v21, v22, v23, v24, v25, v26, v27, v28, v29,
                          v30, v31, v32, v33, v34, v35, v36, v37, v38, v39,
                          v40, v41, v42, v43, v44, v45, v46, v47, v48, v49,
                          v50, v51, v52, v53, v54, v55, v56, v57, v58, v59,
                          v60, v61, v62, v63, v64, v65, v66, v67, v68, v69,
                          v70, v71, v72, v73, v74, v75, v76, v77, v78, v79,
                          v80, v81, v82, v83, v84, v85, v86, v87, v88, v89,
                          v90, v91, v92, v93, v94, v95, v96, v97, v98, v99):
        rgenop = RGenOp()
        gv_largedummyfn = make_largedummy(rgenop)
        largedummyfn = gv_largedummyfn.revealconst(lltype.Ptr(FUNC100))
        res = largedummyfn(v0,  v1,  v2,  v3,  v4,  v5,  v6,  v7,  v8,  v9,
                           v10, v11, v12, v13, v14, v15, v16, v17, v18, v19,
                           v20, v21, v22, v23, v24, v25, v26, v27, v28, v29,
                           v30, v31, v32, v33, v34, v35, v36, v37, v38, v39,
                           v40, v41, v42, v43, v44, v45, v46, v47, v48, v49,
                           v50, v51, v52, v53, v54, v55, v56, v57, v58, v59,
                           v60, v61, v62, v63, v64, v65, v66, v67, v68, v69,
                           v70, v71, v72, v73, v74, v75, v76, v77, v78, v79,
                           v80, v81, v82, v83, v84, v85, v86, v87, v88, v89,
                           v90, v91, v92, v93, v94, v95, v96, v97, v98, v99)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return largedummy_runner

def make_branching(rgenop):
    # 'if x > 5: return x-1
    #  else:     return y'
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, gv_branchingfn, [gv_x, gv_y] = rgenop.newgraph(sigtoken,
                                                            "branching")
    builder.start_writing()
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
    #     z = x * z
    #     y = x + y
    #     x = x - 1
    # y += z
    # return y
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, gv_gotofn, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "goto")
    builder.start_writing()

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
    builder.start_writing()

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
    builder.start_writing()

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
    builder.start_writing()

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
    builder.start_writing()

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
    builder.start_writing()

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
    builder.start_writing()

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
    builder.start_writing()

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

def make_pause_and_resume(rgenop):
    # def f(x):
    #     y = x + 1
    #     # pause/resume here
    #     z = x - 1
    #     w = y*z
    #     return w
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC)
    builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken, "f")
    builder.start_writing()

    gv_one = rgenop.genconst(1)

    gv_y = builder.genop2("int_add", gv_x, gv_one)

    builder = builder.pause_writing([gv_x, gv_y])
    builder.start_writing()

    gv_z = builder.genop2("int_sub", gv_x, gv_one)
    gv_w = builder.genop2("int_mul", gv_y, gv_z)

    builder.finish_and_return(sigtoken, gv_w)

    builder.end()

    return gv_callable

def get_pause_and_resume_runner(RGenOp):
    def runner(x):
        rgenop = RGenOp()
        gv_f = make_pause_and_resume(rgenop)
        f = gv_f.revealconst(lltype.Ptr(FUNC))
        res = f(x)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return runner

def make_something_a_bit_like_residual_red_call_with_exc(rgenop):
    # def f(x, y):
    #     if x:
    #         z = 1
    #         w = 2
    #     else:
    #         z = y+1
    #         w = y
    #     return add1(z*w)
    # but more obfuscated, more like:
    # def f(x, y)
    #     c = x != 0
    #     jump_if_true c, []        ---> finish_and_goto([1, 2])
    #     y = add1(y)                            |
    #     [z, w] = enter_next_block([y, x]) <----'
    #     pause/resume here
    #     z2 = z * w
    #     u = add1(z2)
    #     v = u * z
    #     return add1(u)
    gv_add1 = make_adder(rgenop, 1)
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, gv_f, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "f")
    builder.start_writing()

    gv_c = builder.genop2("int_ne", gv_x, rgenop.genconst(0))

    true_builder = builder.jump_if_true(gv_c, [])

    gv_y2 = builder.genop_call(rgenop.sigToken(FUNC), gv_add1, [gv_y])

    args_gv = [gv_y2, gv_y]
    label = builder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_z, gv_w] = args_gv

    builder = builder.pause_writing(args_gv)
    builder.start_writing()

    gv_z2 = builder.genop2("int_mul", gv_z, gv_w)

    gv_u = builder.genop_call(rgenop.sigToken(FUNC), gv_add1, [gv_z2])

    gv_v = builder.genop2("int_mul", gv_u, gv_z)

    gv_result = builder.genop_call(rgenop.sigToken(FUNC), gv_add1, [gv_u])

    builder.finish_and_return(sigtoken, gv_result)

    true_builder.start_writing()
    true_builder.finish_and_goto([rgenop.genconst(1), rgenop.genconst(2)], label)

    builder.end()
    return gv_f

def make_call_functions_with_different_signatures(rgenop):
    # this also tests calling functions with enormous numbers of
    # parameters, something not tested yet.
    # def f(x, y):
    #     z = largedummy(*((y,)*100))
    #     w = add1(x)
    #     return z+w

    gv_largedummy = make_largedummy(rgenop)
    gv_add1 = make_adder(rgenop, 1)

    sig2token = rgenop.sigToken(FUNC2)
    sig1token = rgenop.sigToken(FUNC)
    sig100token = rgenop.sigToken(FUNC100)
    builder, gv_callable, [gv_x, gv_y] = rgenop.newgraph(sig2token, "f")
    builder.start_writing()

    gv_z = builder.genop_call(sig100token, gv_largedummy, [gv_y]*100)
    gv_w = builder.genop_call(sig1token, gv_add1, [gv_x])
    gv_result = builder.genop2("int_add", gv_z, gv_w)
    builder.finish_and_return(sig2token, gv_result)
    builder.end()

    return gv_callable

class FrameVarReader:
    FUNC = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Signed))
    def __init__(self, RGenOp):
        def reader(base):
            return RGenOp.read_frame_var(lltype.Signed, base,
                                         self.frameinfo, 0)
        self.reader = reader
    def get_reader(self, info):
        self.frameinfo = info
        return llhelper(self.FUNC, self.reader)

def make_read_frame_var(rgenop, get_reader):
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC)
    readertoken = rgenop.sigToken(FrameVarReader.FUNC.TO)

    builder, gv_f, [gv_x] = rgenop.newgraph(sigtoken, "f")
    builder.start_writing()

    gv_y = builder.genop2("int_mul", gv_x, rgenop.genconst(2))
    gv_base = builder.genop_get_frame_base()
    info = builder.get_frame_info([gv_y])
    gv_reader = rgenop.constPrebuiltGlobal(get_reader(info))
    gv_z = builder.genop_call(readertoken, gv_reader, [gv_base])
    builder.finish_and_return(sigtoken, gv_z)
    builder.end()

    return gv_f

def get_read_frame_var_runner(RGenOp):
    fvr = FrameVarReader(RGenOp)

    def read_frame_var_runner(x):
        rgenop = RGenOp()
        gv_f = make_read_frame_var(rgenop, fvr.get_reader)
        fn = gv_f.revealconst(lltype.Ptr(FUNC))
        res = fn(x)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return read_frame_var_runner

class FramePlaceWriter:
    FUNC = lltype.Ptr(lltype.FuncType([llmemory.Address, lltype.Signed],
                                      lltype.Void))
    def __init__(self, RGenOp):
        def writer(base, value):
            if value > 5:
                RGenOp.write_frame_place(lltype.Signed, base,
                                         self.place, value * 7)
        self.writer = writer
    def get_writer(self, place):
        self.place = place
        return llhelper(self.FUNC, self.writer)

def make_write_frame_place(rgenop, get_writer):
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC)
    writertoken = rgenop.sigToken(FramePlaceWriter.FUNC.TO)

    builder, gv_f, [gv_x] = rgenop.newgraph(sigtoken, "f")
    builder.start_writing()

    gv_base = builder.genop_get_frame_base()
    gv_k = rgenop.genconst(-100)
    place = builder.alloc_frame_place(signed_kind, gv_initial_value=gv_k)
    gv_writer = rgenop.constPrebuiltGlobal(get_writer(place))
    builder.genop_call(writertoken, gv_writer, [gv_base, gv_x])
    gv_y = builder.genop_absorb_place(signed_kind, place)
    builder.finish_and_return(sigtoken, gv_y)
    builder.end()

    return gv_f

def get_write_frame_place_runner(RGenOp):
    fvw = FramePlaceWriter(RGenOp)

    def write_frame_place_runner(x):
        rgenop = RGenOp()
        gv_f = make_write_frame_place(rgenop, fvw.get_writer)
        fn = gv_f.revealconst(lltype.Ptr(FUNC))
        res = fn(x)
        keepalive_until_here(rgenop)    # to keep the code blocks alive
        return res
    return write_frame_place_runner


class AbstractRGenOpTests(test_boehm.AbstractGCTestClass):
    RGenOp = None

    def compile(self, runner, argtypes):
        return self.getcompiled(runner, argtypes,
                                annotatorpolicy = GENOP_POLICY)

    def cast(self, gv, nb_args):
        F1 = lltype.FuncType([lltype.Signed] * nb_args, lltype.Signed)
        return self.RGenOp.get_python_callable(lltype.Ptr(F1), gv)

    def directtesthelper(self, FUNCTYPE, func):
        # for machine code backends: build a ctypes function pointer
        # (with a real physical address) that will call back our 'func'
        nb_args = len(FUNCTYPE.TO.ARGS)
        callback = CFUNCTYPE(c_int, *[c_int]*nb_args)(func)
        keepalive = self.__dict__.setdefault('_keepalive', [])
        keepalive.append((callback, func))
        return cast(callback, c_void_p).value
        # NB. returns the address as an integer

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

    def test_largedummy_direct(self):
        rgenop = self.RGenOp()
        gv_largedummyfn = make_largedummy(rgenop)
        fnptr = self.cast(gv_largedummyfn, 100)
        args, expected = largedummy_example()
        res = fnptr(*args)
        assert res == expected

    def test_largedummy_compile(self):
        fn = self.compile(get_largedummy_runner(self.RGenOp), [int] * 100)
        args, expected = largedummy_example()
        res = fn(*args)
        assert res == expected

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
        builder.start_writing()

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
        builder.start_writing()
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
        builder.start_writing()
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
        builder.start_writing()
        builder.finish_and_return(sigtoken, rgenop.genconst(17))
        builder.end()

        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken,
                                                       "jtbwmv")
        builder.start_writing()
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

    def test_same_as(self):
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken, "sameas")
        builder.start_writing()
        gv_nineteen = builder.genop_same_as(signed_kind, rgenop.genconst(19))
        assert not gv_nineteen.is_const   # 'same_as' must return a variable
        builder.finish_and_return(sigtoken, gv_nineteen)
        builder.end()

        fnptr = self.cast(gv_callable, 1)

        res = fnptr(17)
        assert res == 19

    def test_pause_and_resume_direct(self):
        rgenop = self.RGenOp()
        gv_callable = make_pause_and_resume(rgenop)
        fnptr = self.cast(gv_callable, 1)

        res = fnptr(1)
        assert res == 0

        res = fnptr(2)
        assert res == 3

        res = fnptr(3)
        assert res == 8

    def test_pause_and_resume_compile(self):
        fn = self.compile(get_pause_and_resume_runner(self.RGenOp), [int])

        res = fn(1)
        assert res == 0

        res = fn(2)
        assert res == 3

        res = fn(3)
        assert res == 8

    def test_like_residual_red_call_with_exc_direct(self):
        rgenop = self.RGenOp()
        gv_callable = make_something_a_bit_like_residual_red_call_with_exc(rgenop)
        fnptr = self.cast(gv_callable, 2)

        res = fnptr(1, 3)
        assert res == 4

        res = fnptr(0, 3)
        assert res == 14

    def test_call_functions_with_different_signatures_direct(self):
        rgenop = self.RGenOp()
        gv_callable = make_call_functions_with_different_signatures(rgenop)
        fnptr = self.cast(gv_callable, 2)

        res = fnptr(1, 3)
        assert res == 2

        res = fnptr(0, 3)
        assert res == 1

    def test_defaultonly_switch(self):
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken, "defaultonly")
        builder.start_writing()
        flexswitch, default_builder = builder.flexswitch(gv_x, [gv_x])
        default_builder.finish_and_return(sigtoken, gv_x)
        builder.end()

        fnptr = self.cast(gv_callable, 1)

        res = fnptr(17)
        assert res == 17

    def test_bool_not_direct(self):
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        bool_kind = rgenop.kindToken(lltype.Bool)
        sigtoken = rgenop.sigToken(FUNC)
        builder, gv_callable, [gv_x] = rgenop.newgraph(sigtoken, "bool_not")
        builder.start_writing()
        gv_cond = builder.genop2("int_lt", gv_x, rgenop.genconst(10))
        gv_neg  = builder.genop1("bool_not", gv_cond)
        builder2 = builder.jump_if_true(gv_neg, [])
        builder.finish_and_return(sigtoken, rgenop.genconst(111))

        builder2.start_writing()
        builder2.finish_and_return(sigtoken, rgenop.genconst(168))
        builder.end()

        fnptr = self.cast(gv_callable, 1)

        res = fnptr(17)
        assert res == 168
        res = fnptr(7)
        assert res == 111

    def test_read_frame_var_direct(self):
        def get_reader(info):
            fvr = FrameVarReader(self.RGenOp)
            fvr.frameinfo = info
            reader_ptr = self.directtesthelper(fvr.FUNC, fvr.reader)
            return reader_ptr

        rgenop = self.RGenOp()
        gv_callable = make_read_frame_var(rgenop, get_reader)
        fnptr = self.cast(gv_callable, 1)
        res = fnptr(20)
        assert res == 40

    def test_read_frame_var_compile(self):
        fn = self.compile(get_read_frame_var_runner(self.RGenOp), [int])
        res = fn(30)
        assert res == 60

    def test_write_frame_place_direct(self):
        def get_writer(place):
            fvw = FramePlaceWriter(self.RGenOp)
            fvw.place = place
            writer_ptr = self.directtesthelper(fvw.FUNC, fvw.writer)
            return writer_ptr

        rgenop = self.RGenOp()
        gv_callable = make_write_frame_place(rgenop, get_writer)
        fnptr = self.cast(gv_callable, 1)
        res = fnptr(3)
        assert res == -100
        res = fnptr(6)
        assert res == 42

    def test_write_frame_place_compile(self):
        fn = self.compile(get_write_frame_place_runner(self.RGenOp), [int])
        res = fn(-42)
        assert res == -100
        res = fn(606)
        assert res == 4242

    def test_unaliasing_variables_direct(self):
        # def f(x, y):
        #     if x:
        #        a = b = y
        #     else:
        #        a = 2
        #        b = 1
        #     return a+b

        rgenop = self.RGenOp()

        signed_kind = rgenop.kindToken(lltype.Signed)
        sigtoken = rgenop.sigToken(FUNC2)
        builder, gv_callable, [gv_x, gv_y] = rgenop.newgraph(sigtoken, "f")
        builder.start_writing()

        gv_cond = builder.genop1("int_is_true", gv_x)
        false_builder = builder.jump_if_false(gv_cond, [])

        args_gv = [gv_y, gv_y]
        label = builder.enter_next_block([signed_kind, signed_kind], args_gv)
        [gv_a, gv_b] = args_gv

        gv_result = builder.genop2("int_add", gv_a, gv_b)

        builder.finish_and_return(sigtoken, gv_result)

        false_builder.start_writing()
        false_builder.finish_and_goto([rgenop.genconst(2), rgenop.genconst(1)], label)
        builder.end()

        fnptr = self.cast(gv_callable, 2)

        res = fnptr(20, 2)
        assert res == 4

        res = fnptr(0, 2)
        assert res == 3


    def test_from_random_direct(self):
        #def dummyfn(counter, a, b):
        #  goto = 0
        #  while True:
        #    if goto == 0:
        #      b = not a
        #      if a:
        #        counter -= 1
        #        if not counter: break
        #        goto = 0
        #      else:
        #        counter -= 1
        #        if not counter: break
        #        goto = 0
        #  return intmask(a*-468864544+b*-340864157)
        rgenop = self.RGenOp()
        signed_kind = rgenop.kindToken(lltype.Signed)
        bool_kind = rgenop.kindToken(lltype.Bool)

        builder0, gv_callable, [v0, v1, v2] = rgenop.newgraph(rgenop.sigToken(FUNC3), 'compiled_dummyfn')

        builder0.start_writing()
        args_gv = [v0, v1]
        label0 = builder0.enter_next_block([signed_kind, signed_kind], args_gv)
        [v3, v4] = args_gv
        v5 = builder0.genop1('int_is_true', v4)
        builder1 = builder0.jump_if_true(v5, [v3, v4])
        args_gv = [v3, v4, rgenop.genconst(1)]
        label1 = builder0.enter_next_block([signed_kind, signed_kind, bool_kind], args_gv)
        [v6, v7, v8] = args_gv
        v9 = builder0.genop1('int_is_true', v7)
        builder2 = builder0.jump_if_true(v9, [v7, v8, v6])
        v10 = builder0.genop2('int_sub', v6, rgenop.genconst(1))
        v11 = builder0.genop1('int_is_true', v10)
        builder3 = builder0.jump_if_false(v11, [v8, v7])
        builder0.finish_and_goto([v10, v7], label0)

        builder2.start_writing()
        v12 = builder2.genop2('int_sub', v6, rgenop.genconst(1))
        v13 = builder2.genop1('int_is_true', v12)
        builder4 = builder2.jump_if_false(v13, [v8, v7])
        builder2.finish_and_goto([v12, v7], label0)

        builder3.start_writing()
        args_gv = [v8, v7]
        label2 = builder3.enter_next_block([bool_kind, signed_kind], args_gv)
        [v14, v15] = args_gv
        v16 = builder3.genop2('int_mul', v15, rgenop.genconst(-468864544))
        v17 = builder3.genop1('cast_bool_to_int', v14)
        v18 = builder3.genop2('int_mul', v17, rgenop.genconst(-340864157))
        v19 = builder3.genop2('int_add', v16, v18)
        builder3.finish_and_return(rgenop.sigToken(FUNC3), v19)

        builder1.start_writing()
        builder1.finish_and_goto([v3, v4, rgenop.genconst(0)], label1)

        builder4.start_writing()
        builder4.finish_and_goto([v8, v7], label2)
        builder4.end()

        fnptr = self.cast(gv_callable, 3)

        res = fnptr(1, -58, -50)
        assert res == 1424339776
