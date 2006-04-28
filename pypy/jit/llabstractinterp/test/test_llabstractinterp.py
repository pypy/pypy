import py
from pypy.translator.translator import TranslationContext
from pypy.rpython.annlowlevel import annotate_lowlevel_helper
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem import rstr
from pypy.annotation import model as annmodel
from pypy.jit.llabstractinterp.llabstractinterp import LLAbstractInterp, Policy
from pypy.objspace.flow import model as flowmodel
from pypy.rpython import objectmodel

def annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)

_lastinterpreted = []
def get_and_residualize_graph(ll_function, argvalues, arghints, policy):
    key = (ll_function, tuple(arghints),
           tuple([argvalues[n] for n in arghints]), policy)
    for key1, value1 in _lastinterpreted:    # 'key' is not hashable
        if key1 == key:
            return value1
    if len(_lastinterpreted) >= 3:
        del _lastinterpreted[0]
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    a = t.buildannotator()
    argtypes = [annotation(a, value) for value in argvalues]
    graph1 = annotate_lowlevel_helper(a, ll_function, argtypes)
    rtyper = t.buildrtyper()
    rtyper.specialize()
    # build the residual ll graphs by propagating the hints
    interp = LLAbstractInterp(policy)
    hints = {}
    for hint in arghints:
        hints[hint] = argvalues[hint]
    graph2 = interp.eval(graph1, hints)
    # cache and return the original and the residual ll graph
    result = t, interp, graph1, graph2
    _lastinterpreted.append((key, result))
    return result

def abstrinterp(ll_function, argvalues, arghints, policy=Policy()):
    t, interp, graph1, graph2 = get_and_residualize_graph(
        ll_function, argvalues, arghints, policy)
    argvalues2 = [argvalues[n] for n in range(len(argvalues))
                               if n not in arghints]
    rtyper = t.rtyper
    # check the result by running it
    llinterp = LLInterpreter(rtyper)
    result1 = llinterp.eval_graph(graph1, argvalues)
    result2 = llinterp.eval_graph(graph2, argvalues2)
    assert result1 == result2
    return graph2, summary(graph2)

def summary(graph):
    # return a summary of the instructions left in all the residual graphs
    insns = {}
    graphs = [graph]
    found = {graph: True}
    while graphs:
        graph = graphs.pop()
        for block in graph.iterblocks():
            for op in block.operations:
                if op.opname != 'same_as':
                    insns[op.opname] = insns.get(op.opname, 0) + 1
                for arg in op.args:
                    if isinstance(arg, flowmodel.Constant):
                        if (isinstance(arg.concretetype, lltype.Ptr) and
                            isinstance(arg.concretetype.TO, lltype.FuncType)):
                            try:
                                graph = arg.value._obj.graph
                                graph.rgenop
                            except AttributeError:
                                pass
                            else:
                                if graph not in found:
                                    graphs.append(graph)
                                    found[graph] = True
    return insns

P_INLINE = Policy(inlining=True)
P_CONST_INLINE = Policy(inlining=True, const_propagate=True)
P_HINT_DRIVEN = Policy(inlining=True, const_propagate=True, concrete_args=False)


def test_simple():
    def ll_function(x, y):
        return x + y

    graph2, insns = abstrinterp(ll_function, [6, 42], [1])
    # check that the result is "lambda x: x+42"
    assert len(graph2.startblock.operations) == 1
    assert len(graph2.getargs()) == 1
    op = graph2.startblock.operations[0]
    assert op.opname == 'int_add'
    assert op.args[0] is graph2.getargs()[0]
    assert op.args[0].concretetype == lltype.Signed
    assert op.args[1].value == 42
    assert op.args[1].concretetype == lltype.Signed
    assert len(graph2.startblock.exits) == 1
    assert insns == {'int_add': 1}

def test_simple2():
    def ll_function(x, y):
        return x + y
    graph2, insns = abstrinterp(ll_function, [6, 42], [0, 1])
    assert not insns

def test_constantbranch():
    def ll_function(x, y):
        if x:
            y += 1
        y += 2
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [0])
    assert insns == {'int_add': 2}

def test_constantbranch_two_constants():
    def ll_function(x, y):
        if x:
            y += 1
        y += 2
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [0, 1])
    assert not insns

def test_branch():
    def ll_function(x, y):
        if x:
            y += 1
        y += 2
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [])
    assert insns == {'int_is_true': 1, 'int_add': 2}
    graph2, insns = abstrinterp(ll_function, [0, 42], [])
    assert insns == {'int_is_true': 1, 'int_add': 2}

def test_unrolling_loop():
    def ll_function(x, y):
        while x > 0:
            y += x
            x -= 1
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [0])
    assert insns == {'int_add': 6}

def test_loop():
    def ll_function(x, y):
        while x > 0:
            y += x
            x -= 1
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [])
    assert insns == {'int_gt': 1, 'int_add': 1, 'int_sub': 1}

def test_loop2():
    def ll_function(x, y):
        while x > 0:
            y += x
            x -= 1
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [1])
    assert insns == {'int_gt': 2, 'int_add': 2, 'int_sub': 2}

def test_not_merging():
    def ll_function(x, y, z):
        if x:
            a = y + z
        else:
            a = y - z
        a += x
        return a
    graph2, insns = abstrinterp(ll_function, [3, 4, 5], [1, 2])
    assert insns == {'int_is_true': 1, 'int_add': 2}

def test_simple_call():
    def ll2(x, y):
        return x + (y + 42)
    def ll1(x, y, z):
        return ll2(x, y - z)
    graph2, insns = abstrinterp(ll1, [3, 4, 5], [1, 2])
    assert insns == {'direct_call': 1, 'int_add': 1}

def test_simple_struct():
    S = lltype.GcStruct('helloworld', ('hello', lltype.Signed),
                                      ('world', lltype.Signed),
                        hints={'immutable': True})
    s = lltype.malloc(S)
    s.hello = 6
    s.world = 7
    def ll_function(s):
        return s.hello * s.world
    graph2, insns = abstrinterp(ll_function, [s], [0])
    assert insns == {}

def test_simple_array():
    A = lltype.Array(lltype.Char,
                     hints={'immutable': True})
    S = lltype.GcStruct('str', ('chars', A))
    s = lltype.malloc(S, 11)
    for i, c in enumerate("hello world"):
        s.chars[i] = c
    def ll_function(s, i, total):
        while i < len(s.chars):
            total += ord(s.chars[i])
            i += 1
        return total
    graph2, insns = abstrinterp(ll_function, [s, 0, 0], [0, 1, 2])
    assert insns == {}

def no_longer_relevant_test_recursive_call():
    py.test.skip("reimplement or remove the test: "
                 "non-inlined calls with constant results")
    def ll_factorial(k):
        if k <= 1:
            return 1
        else:
            return ll_factorial(k-1) * k
    graph2, insns = abstrinterp(ll_factorial, [7], [0])
    # the direct_calls are messy to count, with calls to ll_stack_check
    assert insns.keys() == ['direct_call']

def test_simple_malloc_removal():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    def ll_function(k):
        s = lltype.malloc(S)
        s.n = k
        l = s.n
        return l+1
    graph2, insns = abstrinterp(ll_function, [7], [0])
    assert insns == {}

def test_inlined_substructure():
    S = lltype.Struct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
    def ll_function(k):
        t = lltype.malloc(T)
        t.s.n = k
        l = t.s.n
        return l
    graph2, insns = abstrinterp(ll_function, [7], [0])
    assert insns == {}

def test_merge_with_inlined_substructure():
    S = lltype.Struct('S', ('n1', lltype.Signed), ('n2', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
    def ll_function(k, flag):
        if flag:
            t = lltype.malloc(T)
            t.s.n1 = k
            t.s.n2 = flag
        else:
            t = lltype.malloc(T)
            t.s.n1 = 14 - k
            t.s.n2 = flag + 42
        # 't.s.n1' should always be 7 here, so the two branches should merge
        n1 = t.s.n1
        n2 = t.s.n2
        return n1 * n2
    graph2, insns = abstrinterp(ll_function, [7, 1], [0])
    assert insns == {'int_is_true': 1, 'int_add': 1, 'int_mul': 1}

def test_dont_merge_forced_and_not_forced():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    def ll_do_nothing(s):
        s.n = 2
    def ll_function(flag):
        s = lltype.malloc(S)
        s.n = 12
        t = s.n
        if flag:
            ll_do_nothing(s)
        return t + s.n
    graph2, insns = abstrinterp(ll_function, [0], [])
    # XXX fragile test: at the moment, the two branches of the 'if' are not
    # being merged at all because 's' was forced in one case only.
    assert insns == {'direct_call': 1, 'int_is_true': 1, 'int_add': 2,
                     'malloc': 1, 'setfield': 1, 'getfield': 1}

def test_unique_virtualptrs():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    def ll_do_nothing(s):
        s.n = 2
    def ll_function(flag, flag2):
        s = lltype.malloc(S)
        s.n = 12
        if flag2:   # flag2 should always be 0
            t = lltype.nullptr(S)
        else:
            t = s
        if flag:
            ll_do_nothing(s)
        return s.n * t.n
    graph2, insns = abstrinterp(ll_function, [1, 0], [])

def test_merge_substructure():
    S = lltype.GcStruct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

    def ll_function(flag):
        t = lltype.malloc(T)
        t.s.n = 3
        s = lltype.malloc(S)
        s.n = 4
        if flag:
            s = t.s
        return s.n+2
    graph2, insns = abstrinterp(ll_function, [0], [])
    assert insns['int_add'] == 2 # no merge

def test_merge_cross_substructure():
    S = lltype.Struct('S', ('n', lltype.Signed))
    T = lltype.GcStruct('T', ('s', S), ('s1', S), ('n', lltype.Float))

    def ll_function(flag):
        t = lltype.malloc(T)
        t.s.n = 3
        t.s1.n = 3
        if flag:
            s = t.s
        else:
            s = t.s1
        n = s.n
        objectmodel.keepalive_until_here(t)
        return n+2
    graph2, insns = abstrinterp(ll_function, [0], [])
    assert insns['int_add'] == 2 # no merge

def test_merge_different_sharing():
    S = lltype.GcStruct('S', ('x', lltype.Signed), ('y', lltype.Signed))
    T = lltype.GcStruct('T', ('s1', lltype.Ptr(S)), ('s2', lltype.Ptr(S)))
    def ll_function(flag, x,y):
        if flag:
            t = lltype.malloc(T)
            s = lltype.malloc(S)
            s.x = x
            s.y = y
            t.s1 = s
            t.s2 = s
        else:
            t = lltype.malloc(T)
            s1 = lltype.malloc(S)
            s2 = lltype.malloc(S)
            s1.x = x
            s2.x = x
            s1.y = y
            s2.y = y
            t.s1 = s1
            t.s2 = s2
        # the two t joining here are not mergeable
        return (t.s1.x+t.s1.x)*(t.s2.y+t.s2.y)
    graph2, insns = abstrinterp(ll_function, [0, 2, 3], [])
    # no merge
    assert insns['int_add'] == 4
    assert insns['int_mul'] == 2    
            
def test_cast_pointer():
    S = lltype.GcStruct('S', ('n1', lltype.Signed), ('n2', lltype.Signed))
    PS = lltype.Ptr(S)
    T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))
    def ll_function():
        t = lltype.malloc(T)
        s = lltype.cast_pointer(PS, t)
        t.s.n1 = 12
        return s.n1
    graph2, insns = abstrinterp(ll_function, [], [])
    assert insns == {}

def test_residual_direct_call():
    def ll_uninteresting(x, y):
        return x * y
    def ll_function(a, b):
        return ll_uninteresting(a+b, b+1)
    graph2, insns = abstrinterp(ll_function, [2, 5], [0])
    # ll_uninteresting() should not be residualized because it is only passed
    # non-concrete values, so 'insns' should only see the residualized
    # ll_function().
    assert insns == {'direct_call': 1, 'int_add': 2}

def test_virtual_array():
    A = lltype.GcArray(lltype.Signed)
    def ll_function(k, l):
        a = lltype.malloc(A, 3)
        a[0] = k
        a[1] = 12
        a[2] = l
        return (a[0] + a[1]) + a[2]
    graph2, insns = abstrinterp(ll_function, [7, 983], [0])
    assert insns == {'int_add': 1}

def test_simple_call_with_inlining():
    def ll2(x, y):
        return x + (y + 42)
    def ll1(x, y, z):
        return ll2(x, y - z)
    graph2, insns = abstrinterp(ll1, [3, 4, 5], [1, 2], policy=P_INLINE)
    assert insns == {'int_add': 1}

def test_const_propagate():
    def ll_add(x, y):
        return x + y
    def ll1(x):
        return ll_add(x, 42)
    graph2, insns = abstrinterp(ll1, [3], [0], policy=P_CONST_INLINE)
    assert insns == {}

def test_dont_unroll_loop():
    def ll_factorial(n):
        i = 1
        result = 1
        while i < n:
            i += 1
            result *= i
        return result
    graph2, insns = abstrinterp(ll_factorial, [7], [], policy=P_CONST_INLINE)
    assert insns == {'int_lt': 1, 'int_add': 1, 'int_mul': 1}

def test_hint():
    from pypy.rpython.objectmodel import hint
    A = lltype.GcArray(lltype.Char, hints={'immutable': True})
    def ll_interp(code):
        accum = 0
        pc = 0
        while pc < len(code):
            opcode = hint(code[pc], concrete=True)
            pc += 1
            if opcode == 'A':
                accum += 6
            elif opcode == 'B':
                if accum < 20:
                    pc = 0
        return accum
    bytecode = lltype.malloc(A, 5)
    bytecode[0] = 'A'
    bytecode[1] = 'A'
    bytecode[2] = 'A'
    bytecode[3] = 'B'
    bytecode[4] = 'A'
    graph2, insns = abstrinterp(ll_interp, [bytecode], [0],
                                policy=P_HINT_DRIVEN)
    assert insns == {'int_add': 4, 'int_lt': 1}

def test_hint_across_call():
    from pypy.rpython.objectmodel import hint
    A = lltype.GcArray(lltype.Char, hints={'immutable': True})
    def ll_length(a):
        return len(a)
    def ll_getitem(a, i):
        return a[i]
    def ll_interp(code):
        accum = 0
        pc = 0
        while pc < ll_length(code):
            opcode = hint(ll_getitem(code, pc), concrete=True)
            pc += 1
            if opcode == 'A':
                accum += 6
            elif opcode == 'B':
                if accum < 20:
                    pc = 0
        return accum
    bytecode = lltype.malloc(A, 5)
    bytecode[0] = 'A'
    bytecode[1] = 'A'
    bytecode[2] = 'A'
    bytecode[3] = 'B'
    bytecode[4] = 'A'
    graph2, insns = abstrinterp(ll_interp, [bytecode], [0],
                                policy=P_HINT_DRIVEN)
    assert insns == {'int_add': 4, 'int_lt': 1}

def test_conditional_origin():
    from pypy.rpython.objectmodel import hint
    def ll_function(x, y, variable):
        result = 0
        i = 0
        while i < 10:
            if i:
                z = x
            else:
                z = y
            z = hint(z, concrete=True)
            if z == 42:
                result += variable
            i += 1
        return result
    graph2, insns = abstrinterp(ll_function, [42, 71298, -12], [0, 1],
                                policy=P_HINT_DRIVEN)
    # the result is not really specified.  In theory, the hint() call could
    # fix 'i', because 'z' depends on 'i'.  Then we'd get:
    #    assert insns == {'int_add': 9}
    #
    # But llabstractinterp doesn't track this particular dependency for now,
    # so what we get is:
    assert insns == {'int_lt': 1, 'int_is_true': 1, 'int_add': 2}
