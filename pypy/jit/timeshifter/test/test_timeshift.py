import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.bookkeeper import HintBookkeeper
from pypy.jit.hintannotator.model import *
from pypy.jit.timeshifter.timeshift import HintTimeshift
from pypy.jit.timeshifter import rtimeshift, rtyper as hintrtyper
from pypy.jit.llabstractinterp.test.test_llabstractinterp import annotation
from pypy.jit.llabstractinterp.test.test_llabstractinterp import summary
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.objectmodel import hint, keepalive_until_here
from pypy.rpython import rgenop
from pypy.rpython.lltypesystem import rstr
from pypy.annotation import model as annmodel
from pypy.rpython.llinterp import LLInterpreter
from pypy.objspace.flow.model import checkgraph
from pypy.annotation.policy import AnnotatorPolicy
from pypy.translator.backendopt.inline import auto_inlining
from pypy import conftest

P_NOVIRTUAL = AnnotatorPolicy()
P_NOVIRTUAL.novirtualcontainer = True
P_NOVIRTUAL.oopspec = True

def getargtypes(annotator, values):
    return [annotation(annotator, x) for x in values]

def hannotate(func, values, policy=None, inline=None):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    a = t.buildannotator()
    argtypes = getargtypes(a, values)
    a.build_types(func, argtypes)
    rtyper = t.buildrtyper()
    rtyper.specialize()
    if inline:
        auto_inlining(t, inline)
    graph1 = graphof(t, func)
    # build hint annotator types
    hannotator = HintAnnotator(policy=policy)
    hannotator.base_translator = t
    hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                {OriginFlags(): True})
                                         for v in graph1.getargs()])
    if conftest.option.view:
        hannotator.translator.view()
    return hs, hannotator, rtyper

_cache = {}
_cache_order = []
def timeshift_cached(ll_function, values, inline, policy):
    key = ll_function, inline, policy
    try:
        result, argtypes = _cache[key]
    except KeyError:
        if len(_cache_order) >= 3:
            del _cache[_cache_order.pop(0)]
        hs, ha, rtyper = hannotate(ll_function, values,
                                   inline=inline, policy=policy)
        htshift = HintTimeshift(ha, rtyper)
        htshift.timeshift()
        t = rtyper.annotator.translator
        for graph in ha.translator.graphs:
            checkgraph(graph)
            t.graphs.append(graph)
        if conftest.option.view:
            from pypy.translator.tool.graphpage import FlowGraphPage
            FlowGraphPage(t, ha.translator.graphs).display()
        result = hs, ha, rtyper, htshift
        _cache[key] = result, getargtypes(rtyper.annotator, values)
        _cache_order.append(key)
    else:
        hs, ha, rtyper, htshift = result
        assert argtypes == getargtypes(rtyper.annotator, values)
    return result

def timeshift(ll_function, values, opt_consts=[], inline=None, policy=None):
    hs, ha, rtyper, htshift = timeshift_cached(ll_function, values,
                                               inline, policy)
    # run the time-shifted graph-producing graphs
    graph1 = ha.translator.graphs[0]
    llinterp = LLInterpreter(rtyper)
    llinterp.eval_graph(htshift.ll_clearcaches, [])
    jitstate = llinterp.eval_graph(htshift.ll_build_jitstate_graph, [])
    graph1args = [jitstate]
    residual_graph_args = []
    assert len(graph1.getargs()) == 1 + len(values)
    for i, (v, llvalue) in enumerate(zip(graph1.getargs()[1:], values)):
        r = htshift.hrtyper.bindingrepr(v)
        residual_v = r.residual_values(llvalue)
        if len(residual_v) == 0:
            # green
            graph1args.append(llvalue)
        else:
            # red
            assert residual_v == [llvalue], "XXX for now"
            TYPE = htshift.originalconcretetype(v)
            gv_type = rgenop.constTYPE(TYPE)
            gvar = llinterp.eval_graph(htshift.ll_geninputarg_graph, [jitstate,
                                                                      gv_type])
            if i in opt_consts: # XXX what should happen here interface wise is unclear
                gvar = rgenop.genconst(llvalue)
            if isinstance(lltype.typeOf(llvalue), lltype.Ptr):
                ll_box_graph = htshift.ll_addr_box_graph
            elif isinstance(llvalue, float):
                ll_box_graph = htshift.ll_double_box_graph
            else:
                ll_box_graph = htshift.ll_int_box_graph
            box = llinterp.eval_graph(ll_box_graph, [gv_type, gvar])
            graph1args.append(box)
            residual_graph_args.append(llvalue)
    startblock = llinterp.eval_graph(htshift.ll_end_setup_jitstate_graph, [jitstate])

    newjitstate = llinterp.eval_graph(graph1, graph1args)
    # now try to run the blocks produced by the jitstate
    r = htshift.hrtyper.getrepr(hs)
    llinterp.eval_graph(htshift.ll_close_jitstate_graph, [jitstate])

    residual_graph = rgenop.buildgraph(startblock)
    insns = summary(residual_graph)
    res = rgenop.testgengraph(residual_graph, residual_graph_args,
                              viewbefore = conftest.option.view)
    return insns, res

##def test_ll_get_return_queue():
##    t = TranslationContext()
##    a = t.buildannotator()
##    rtyper = t.buildrtyper()
##    rtyper.specialize() # XXX

##    htshift = HintTimeshift(None, rtyper)

##    questate = htshift.QUESTATE_PTR.TO.ll_newstate()

##    def llf(questate):
##        return questate.ll_get_return_queue()

##    from pypy.rpython import annlowlevel

##    graph = annlowlevel.annotate_mixlevel_helper(rtyper, llf, [
##        annmodel.SomePtr(htshift.QUESTATE_PTR)])

##    s = a.binding(graph.getreturnvar())

##    assert s == htshift.s_return_queue

##    rtyper.specialize_more_blocks()

##    llinterp = LLInterpreter(rtyper)
##    rq = llinterp.eval_graph(graph, [questate])
##    assert lltype.typeOf(rq) == rtyper.getrepr(s).lowleveltype


def test_simple_fixed():
    def ll_function(x, y):
        return hint(x + y, concrete=True)
    insns, res = timeshift(ll_function, [5, 7])
    assert res == 12
    assert insns == {}

def test_simple():
    def ll_function(x, y):
        return x + y
    insns, res = timeshift(ll_function, [5, 7])
    assert res == 12
    assert insns == {'int_add': 1}

def test_convert_const_to_redbox():
    def ll_function(x, y):
        x = hint(x, concrete=True)
        tot = 0
        while x:    # conversion from green '0' to red 'tot'
            tot += y
            x -= 1
        return tot
    insns, res = timeshift(ll_function, [7, 2])
    assert res == 14
    assert insns == {'int_add': 7}

def test_simple_opt_const_propagation2():
    def ll_function(x, y):
        return x + y
    insns, res = timeshift(ll_function, [5, 7], [0, 1])
    assert res == 12
    assert insns == {}

def test_simple_opt_const_propagation1():
    def ll_function(x):
        return -x
    insns, res = timeshift(ll_function, [5], [0])
    assert res == -5
    assert insns == {}

def test_loop_folding():
    def ll_function(x, y):
        tot = 0
        x = hint(x, concrete=True)        
        while x:
            tot += y
            x -= 1
        return tot
    insns, res = timeshift(ll_function, [7, 2], [0, 1])
    assert res == 14
    assert insns == {}

def test_loop_merging():
    def ll_function(x, y):
        tot = 0
        while x:
            tot += y
            x -= 1
        return tot
    insns, res = timeshift(ll_function, [7, 2], [])
    assert res == 14
    assert insns['int_add'] == 2
    assert insns['int_is_true'] == 2

    insns, res = timeshift(ll_function, [7, 2], [0])
    assert res == 14
    assert insns['int_add'] == 2
    assert insns['int_is_true'] == 1

    insns, res = timeshift(ll_function, [7, 2], [1])
    assert res == 14
    assert insns['int_add'] == 1
    assert insns['int_is_true'] == 2

    insns, res = timeshift(ll_function, [7, 2], [0, 1])
    assert res == 14
    assert insns['int_add'] == 1
    assert insns['int_is_true'] == 1

def test_two_loops_merging():
    def ll_function(x, y):
        tot = 0
        while x:
            tot += y
            x -= 1
        while y:
            tot += y
            y -= 1
        return tot
    insns, res = timeshift(ll_function, [7, 3], [])
    assert res == 27
    assert insns['int_add'] == 3
    assert insns['int_is_true'] == 3

def test_convert_greenvar_to_redvar():
    def ll_function(x, y):
        hint(x, concrete=True)
        return x - y
    insns, res = timeshift(ll_function, [70, 4], [0])
    assert res == 66
    assert insns['int_sub'] == 1
    insns, res = timeshift(ll_function, [70, 4], [0, 1])
    assert res == 66
    assert insns == {}

def test_green_across_split():
    def ll_function(x, y):
        hint(x, concrete=True)
        if y > 2:
            z = x - y
        else:
            z = x + y
        return z
    insns, res = timeshift(ll_function, [70, 4], [0])
    assert res == 66
    assert insns['int_add'] == 1
    assert insns['int_sub'] == 1

def test_merge_const_before_return():
    def ll_function(x):
        if x > 0:
            y = 17
        else:
            y = 22
        x -= 1
        y += 1
        return y+x
    insns, res = timeshift(ll_function, [-70], [])
    assert res == 23-71
    assert insns == {'int_gt': 1, 'int_add': 2, 'int_sub': 2}

def test_merge_3_redconsts_before_return():
    def ll_function(x):
        if x > 2:
            y = hint(54, variable=True)
        elif x > 0:
            y = hint(17, variable=True)
        else:
            y = hint(22, variable=True)
        x -= 1
        y += 1
        return y+x
    insns, res = timeshift(ll_function, [-70], [])
    assert res == ll_function(-70)
    insns, res = timeshift(ll_function, [1], [])
    assert res == ll_function(1)
    insns, res = timeshift(ll_function, [-70], [])
    assert res == ll_function(-70)

def test_merge_const_at_return():
    def ll_function(x):
        if x > 0:
            return 17
        else:
            return 22
    insns, res = timeshift(ll_function, [-70], [])
    assert res == 22
    assert insns == {'int_gt': 1}

def test_arith_plus_minus():
    def ll_plus_minus(encoded_insn, nb_insn, x, y):
        acc = x
        pc = 0
        while pc < nb_insn:
            op = (encoded_insn >> (pc*4)) & 0xF
            op = hint(op, concrete=True)
            if op == 0xA:
                acc += y
            elif op == 0x5:
                acc -= y
            pc += 1
        return acc
    assert ll_plus_minus(0xA5A, 3, 32, 10) == 42
    insns, res = timeshift(ll_plus_minus, [0xA5A, 3, 32, 10], [0, 1])
    assert res == 42
    assert insns == {'int_add': 2,
                     'int_sub': 1}

def test_simple_struct():
    S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                      ('world', lltype.Signed),
                        hints={'immutable': True})
    def ll_function(s):
        return s.hello * s.world
    s1 = lltype.malloc(S)
    s1.hello = 6
    s1.world = 7
    insns, res = timeshift(ll_function, [s1], [])
    assert res == 42
    assert insns == {'getfield': 2,
                     'int_mul': 1}
    insns, res = timeshift(ll_function, [s1], [0])
    assert res == 42
    assert insns == {}

def test_simple_array():
    A = lltype.GcArray(lltype.Signed, 
                        hints={'immutable': True})
    def ll_function(a):
        return a[0] * a[1]
    a1 = lltype.malloc(A, 2)
    a1[0] = 6
    a1[1] = 7
    insns, res = timeshift(ll_function, [a1], [])
    assert res == 42
    assert insns == {'getarrayitem': 2,
                     'int_mul': 1}
    insns, res = timeshift(ll_function, [a1], [0])
    assert res == 42
    assert insns == {}

def test_simple_struct_malloc():
    py.test.skip("blue containers: to be reimplemented")
    S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                      ('world', lltype.Signed))               
    def ll_function(x):
        s = lltype.malloc(S)
        s.hello = x
        return s.hello + s.world

    insns, res = timeshift(ll_function, [3], [])
    assert res == 3
    assert insns == {'int_add': 1}

    insns, res = timeshift(ll_function, [3], [0])
    assert res == 3
    assert insns == {}

def test_inlined_substructure():
    py.test.skip("blue containers: to be reimplemented")
    S = lltype.Struct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
    def ll_function(k):
        t = lltype.malloc(T)
        t.s.n = k
        l = t.s.n
        return l
    insns, res = timeshift(ll_function, [7], [])
    assert res == 7
    assert insns == {}

    insns, res = timeshift(ll_function, [7], [0])
    assert res == 7
    assert insns == {}    

def test_degenerated_before_return():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

    def ll_function(flag):
        t = lltype.malloc(T)
        t.s.n = 3
        s = lltype.malloc(S)
        s.n = 4
        if flag:
            s = t.s
        s.n += 1
        return s.n * t.s.n
    insns, res = timeshift(ll_function, [0], [])
    assert res == 5 * 3
    insns, res = timeshift(ll_function, [1], [])
    assert res == 4 * 4

def test_degenerated_before_return_2():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

    def ll_function(flag):
        t = lltype.malloc(T)
        t.s.n = 3
        s = lltype.malloc(S)
        s.n = 4
        if flag:
            pass
        else:
            s = t.s
        s.n += 1
        return s.n * t.s.n
    insns, res = timeshift(ll_function, [1], [])
    assert res == 5 * 3
    insns, res = timeshift(ll_function, [0], [])
    assert res == 4 * 4

def test_degenerated_at_return():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

    def ll_function(flag):
        t = lltype.malloc(T)
        t.n = 3.25
        t.s.n = 3
        s = lltype.malloc(S)
        s.n = 4
        if flag:
            s = t.s
        return s
    insns, res = timeshift(ll_function, [0], [])
    assert res.n == 4
    assert lltype.parentlink(res._obj) == (None, None)
    insns, res = timeshift(ll_function, [1], [])
    assert res.n == 3
    parent, parentindex = lltype.parentlink(res._obj)
    assert parentindex == 's'
    assert parent.n == 3.25

def test_degenerated_via_substructure():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

    def ll_function(flag):
        t = lltype.malloc(T)
        t.s.n = 3
        s = lltype.malloc(S)
        s.n = 7
        if flag:
            pass
        else:
            s = t.s
        t.s.n += 1
        return s.n * t.s.n
    insns, res = timeshift(ll_function, [1], [])
    assert res == 7 * 4
    insns, res = timeshift(ll_function, [0], [])
    assert res == 4 * 4

def test_plus_minus_all_inlined():
    def ll_plus_minus(s, x, y):
        acc = x
        n = len(s)
        pc = 0
        while pc < n:
            op = s[pc]
            op = hint(op, concrete=True)
            if op == '+':
                acc += y
            elif op == '-':
                acc -= y
            pc += 1
        return acc
    s = rstr.string_repr.convert_const("+-+")
    insns, res = timeshift(ll_plus_minus, [s, 0, 2], [0], inline=999)
    assert res == ll_plus_minus("+-+", 0, 2)
    assert insns == {'int_add': 2, 'int_sub': 1}

def test_red_virtual_container():
    # this checks that red boxes are able to be virtualized dynamically by
    # the compiler (the P_NOVIRTUAL policy prevents the hint-annotator from
    # marking variables in blue)
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    def ll_function(n):
        s = lltype.malloc(S)
        s.n = n
        return s.n
    insns, res = timeshift(ll_function, [42], [], policy=P_NOVIRTUAL)
    assert res == 42
    assert insns == {}

def test_red_propagate():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    def ll_function(n, k):
        s = lltype.malloc(S)
        s.n = n
        if k < 0:
            return -123
        return s.n * k
    insns, res = timeshift(ll_function, [3, 8], [], policy=P_NOVIRTUAL)
    assert res == 24
    assert insns == {'int_lt': 1, 'int_mul': 1}

def test_red_subcontainer():
    S = lltype.Struct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
    def ll_function(k):
        t = lltype.malloc(T)
        s = t.s
        s.n = k
        if k < 0:
            return -123
        result = s.n * (k-1)
        keepalive_until_here(t)
        return result
    insns, res = timeshift(ll_function, [7], [], policy=P_NOVIRTUAL)
    assert res == 42
    assert insns == {'int_lt': 1, 'int_mul': 1, 'int_sub': 1}

def test_merge_structures():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', lltype.Ptr(S)), ('n', lltype.Signed))

    def ll_function(flag):
        if flag:
            s = lltype.malloc(S)
            s.n = 1
            t = lltype.malloc(T)
            t.s = s
            t.n = 2
        else:
            s = lltype.malloc(S)
            s.n = 5
            t = lltype.malloc(T)
            t.s = s
            t.n = 6
        return t.n + t.s.n
    insns, res = timeshift(ll_function, [0], [], policy=P_NOVIRTUAL)
    assert res == 5 + 6
    assert insns == {'int_is_true': 1, 'int_add': 1}
    insns, res = timeshift(ll_function, [1], [], policy=P_NOVIRTUAL)
    assert res == 1 + 2
    assert insns == {'int_is_true': 1, 'int_add': 1}

def test_vlist():
    py.test.skip("in-progress")
    def ll_function():
        lst = []
        lst.append(12)
        return lst[0]
    insns, res = timeshift(ll_function, [], [], policy=P_NOVIRTUAL)
    assert res == 12
    assert insns == {}
