from pypy.jit.codegen.llgraph.rgenop import rgenop
from pypy.jit.codegen.llgraph.llimpl import testgengraph
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.test.test_llinterp import interpret as _interpret
from pypy.rpython.module.support import from_opaque_object
from pypy.objspace.flow import model as flowmodel
from pypy.rpython import annlowlevel

class GenconstPolicy(annlowlevel.MixLevelAnnotatorPolicy):

    def __init__(self):
        pass

genconst_policy = GenconstPolicy()

def interpret(fn, args):
    return _interpret(fn, args, policy=genconst_policy)

F1 = lltype.FuncType([lltype.Signed], lltype.Signed)
F2 = lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed)
f1_token = rgenop.sigToken(F1)
f2_token = rgenop.sigToken(F2)
signed_tok = rgenop.kindToken(lltype.Signed)

def runner(build):
    def run(x):
        fptr = build()
        return fptr(x)
    return run

def runner2(build):
    def run(x, y):
        fptr = build()
        return fptr(x, y)
    return run


def build_square():
    """def square(v0): return v0*v0"""
    builder, gv_square, (gv0,) = rgenop.newgraph(f1_token, "square")
    gv1 = builder.genop2('int_mul', gv0, gv0)
    builder.finish_and_return(f1_token, gv1)
    builder.end()
    square_ptr = gv_square.revealconst(lltype.Ptr(F1))
    return square_ptr


def test_square():
    square_ptr = build_square()
    res = testgengraph(square_ptr._obj.graph, [17])
    assert res == 289
    
def test_interpret_square():
    res = interpret(runner(build_square), [17])
    assert res == 289

def build_if():
    """
    def f(v0):
        if v0 < 0:
            return 0
        else:
            return v0
    """
    builder, gv_if, (gv0,) = rgenop.newgraph(f1_token, "if")
 
    const0 = rgenop.genconst(0)
    gv1 = builder.genop2('int_lt', gv0, const0)
    false_builder = builder.jump_if_false(gv1, [gv0])
    builder.finish_and_return(f1_token, const0)
    false_builder.start_writing()
    false_builder.finish_and_return(f1_token, gv0)
    builder.end()
    if_ptr = gv_if.revealconst(lltype.Ptr(F1))
    return if_ptr

def test_if():
    if_ptr = build_if()
    if_graph = if_ptr._obj.graph
    res = testgengraph(if_graph, [-1])
    assert res == 0
    res = testgengraph(if_graph, [42])
    assert res == 42

def test_interpret_if():
    run_if = runner(build_if)
    res = interpret(run_if, [-1])
    assert res == 0
    res = interpret(run_if, [42])
    assert res == 42

def build_loop():
    """
    def f(v0):
        i = 1
        result = 1
        while True:
            result *= i
            i += 1
            if i > v0: break
        return result
    """
    builder, gv_loop, (gv0,) = rgenop.newgraph(f1_token, "loop")
    const1 = rgenop.genconst(1)

    args_gv = [const1, const1, gv0]
    loopblock = builder.enter_next_block([signed_tok, signed_tok, signed_tok],
                                         args_gv)
    gv_result0, gv_i0, gv1 = args_gv
    gv_result1 = builder.genop2('int_mul', gv_result0, gv_i0)
    gv_i1 = builder.genop2('int_add', gv_i0, const1)
    gv2 = builder.genop2('int_le', gv_i1, gv1)
    loop_builder = builder.jump_if_true(gv2, [gv_result1, gv_i1, gv1])
    builder.finish_and_return(f1_token, gv_result1)
    loop_builder.start_writing()
    loop_builder.finish_and_goto([gv_result1, gv_i1, gv1], loopblock)

    builder.end()
    loop_ptr = gv_loop.revealconst(lltype.Ptr(F1))
    return loop_ptr

def test_loop():
    loop_ptr = build_loop()
    loop_graph = loop_ptr._obj.graph
    res = testgengraph(loop_graph, [0])
    assert res == 1
    res = testgengraph(loop_graph, [1])
    assert res == 1
    res = testgengraph(loop_graph, [7])
    assert res == 5040

def test_interpret_loop():
    run_loop = runner(build_loop)
    res = interpret(run_loop, [0])
    assert res == 1
    res = interpret(run_loop, [1])
    assert res == 1
    res = interpret(run_loop, [7])
    assert res == 5040


def test_interpret_revealcosnt():
    def hide_and_reveal(v):
        gv = rgenop.genconst(v)
        return gv.revealconst(lltype.Signed)
    res = interpret(hide_and_reveal, [42])
    assert res == 42

    S = lltype.GcStruct('s', ('x', lltype.Signed))
    S_PTR = lltype.Ptr(S)
    def hide_and_reveal_p(p):
        gv = rgenop.genconst(p)
        return gv.revealconst(S_PTR)
    s = lltype.malloc(S)
    res = interpret(hide_and_reveal_p, [s])
    assert res == s


def build_switch():
    """
    def f(v0, v1):
        if v0 == 0: # switch
            return 21*v1
        elif v0 == 1:
            return 21+v1
        else:
            return v1
    """
    builder, gv_switch, (gv0, gv1) = rgenop.newgraph(f2_token, "switch")

    flexswitch, default_builder = builder.flexswitch(gv0, [gv1])
    const21 = rgenop.genconst(21)

    # case == 0
    const0 = rgenop.genconst(0)
    case_builder = flexswitch.add_case(const0)
    gv_res_case0 = case_builder.genop2('int_mul', const21, gv1)
    case_builder.finish_and_return(f2_token, gv_res_case0)
    # case == 1
    const1 = rgenop.genconst(1)
    case_builder = flexswitch.add_case(const1)
    gv_res_case1 = case_builder.genop2('int_add', const21, gv1)
    case_builder.finish_and_return(f2_token, gv_res_case1)
    # default
    default_builder.finish_and_return(f2_token, gv1)

    builder.end()
    switch_ptr = gv_switch.revealconst(lltype.Ptr(F2))
    return switch_ptr

def test_switch():
    switch_ptr = build_switch()
    switch_graph = switch_ptr._obj.graph
    res = testgengraph(switch_graph, [0, 2])
    assert res == 42
    res = testgengraph(switch_graph, [1, 16])
    assert res == 37
    res = testgengraph(switch_graph, [42, 16])
    assert res == 16

def test_interpret_switch():
    run_switch = runner2(build_switch)
    res = interpret(run_switch, [0, 2])
    assert res == 42
    res = interpret(run_switch, [1, 15])
    assert res == 36
    res = interpret(run_switch, [42, 5])
    assert res == 5
