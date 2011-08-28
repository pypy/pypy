import py
import os
from pypy.translator.stackless.transform import StacklessTransformer, FrameTyper
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.translator.c import gc
from pypy.translator.unsimplify import varoftype
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import llinterp
from pypy.rlib import rstack
from pypy.translator.translator import TranslationContext, graphof
from pypy.objspace.flow.model import checkgraph
from pypy.annotation import model as annmodel
from pypy.annotation.listdef import s_list_of_strings
from pypy import conftest

def test_frame_typer():
    class TestFrameTyper(FrameTyper):
        def saving_function_for_type(self, frame_type):
            return None
    ft = TestFrameTyper()
    ft4vars = lambda types:ft.frame_type_for_vars(types)[0]

    signed = varoftype(lltype.Signed)
    ptr = varoftype(lltype.Ptr(lltype.GcStruct("S")))
    addr = varoftype(llmemory.Address)
    float = varoftype(lltype.Float)
    longlong = varoftype(lltype.SignedLongLong)

    
    s1_1 = ft4vars([signed])
    assert 'header' in s1_1._flds
    assert len(s1_1._flds) == 2
    s1_2 = ft4vars([signed])
    assert s1_1 is s1_2

    s2_1 = ft4vars([signed, ptr])
    s2_2 = ft4vars([ptr, signed])

    assert s2_1 is s2_2

def factorial(n):
    if n > 1:
        return factorial(n-1) * n
    else:
        return 1

def one():   # but the annotator doesn't know it's one
    return factorial(5) / 120


def test_nothing():
    def fn():
        return 21
    res = llinterp_stackless_function(fn, assert_unwind=False)
    assert res == 21
    info = py.test.raises(
        llinterp.LLException,
        "llinterp_stackless_function(fn, assert_unwind=True)")
    assert ''.join(info.value.args[0].name).strip('\x00') == "AssertionError"        

def test_simple_transform_llinterp():
    def check(x):
        if x:
            rstack.stack_unwind()
    def g(x):
        check(x)
        return x + 1
    def example():
        return g(one()) + 1
    res = llinterp_stackless_function(example)
    assert res == 3

def test_simple_transform_llinterp_float():
    def check(x):
        if x:
            rstack.stack_unwind()
    def g(x):
        check(x)
        return x + 0.125
    def example():
        return int((g(one()) + 1)*1000.0)
    res = llinterp_stackless_function(example)
    assert res == 2125

def test_simple_transform_compiled():
    def check(x):
        if x:
            rstack.stack_unwind()
    def g(x):
        check(x)
        return x + 1
    def example():
        return g(one()) + 1
    res = run_stackless_function(example)
    assert res == 3

def test_protected_call():
    def check(x):
        if x:
            rstack.stack_unwind()
    def g(x):
        check(x)
        return x + 1
    def example():
        try:
            y = g(one())
        except Exception:
            y = -1
        return y + 1
    res = llinterp_stackless_function(example)
    assert res == 3
    res = run_stackless_function(example)
    assert res == 3

def test_resume_with_exception():
    def check(x):
        if x:
            rstack.stack_unwind()
    def g(x):
        check(x)
        if x:
            raise KeyError
        else:
            return x + 1
    def h(x):
        return g(x)
    def example():
        y = h(one())
        return y + 1
    info = py.test.raises(
        llinterp.LLException,
        "llinterp_stackless_function(example)")
    assert llinterp.type_name(info.value.args[0]) == 'KeyError'

def test_resume_with_exception_handling():
    def check(x):
        if x:
            rstack.stack_unwind()
    def g(x):
        check(x)
        if x:
            raise KeyError
        else:
            return x + 1
    def h(x):
        return g(x)
    def example():
        try:
            y = h(one())
        except KeyError:
            y = -one()
        return y + 1
    res = llinterp_stackless_function(example)
    assert res == 0

def test_resume_with_exception_handling_with_vals():
    def check(x):
        if x:
            rstack.stack_unwind()
    def g(x):
        check(x)
        if x:
            raise KeyError
        else:
            return x + 1
    def h(x):
        return g(x)
    def example():
        y = one()
        try:
            y = h(one())
        except KeyError:
            y = y - 2
        return y + 1
    res = llinterp_stackless_function(example)
    assert res == 0

def test_listcomp():
    def check(x):
        if x:
            rstack.stack_unwind()
    def f():
        l = one()
        check(l)
        return len([x for x in range(l)])
    res = llinterp_stackless_function(f)
    assert res == 1

def test_constant_on_link():
    class A(object):
        pass
    def stuff(m):
        if m > 100:
            raise KeyError
        a = A()
        rstack.stack_unwind()
        a.m = m + 5
        return a
    def g(n, m):
        a = A()
        if m > 0:
            try:
                a = stuff(m)
            except KeyError:
                return -1
            n = 100
        return a.m + n
    def f():
        return g(one(), one())
    res = llinterp_stackless_function(f)
    assert res == 106

def test_dont_transform_too_much():
    def check(x):
        if x:
            rstack.stack_unwind()
    def f(x):
        return x + 2
    def g(x):
        check(x)
        return f(x) + x + 1
    def example():
        return g(one()) + 1
    res, t = llinterp_stackless_function(example, returntranslator=True)
    assert res == 6

    ggraph = graphof(t, g)
    for block, op in ggraph.iterblockops():
        if op.opname == 'direct_call':
            if op.args[0].value._obj._callable is f:
                assert op != block.operations[-1]

def test_void_around():
    def f():
        return 6
    def getf():
        return f
    def g():
        f1 = getf()
        for i in range(5):
            rstack.stack_unwind()
        return f1
    def example():
        return g()()
    res = llinterp_stackless_function(example)
    assert res == 6

def rtype_stackless_function(fn):
    t = TranslationContext()
    t.config.translation.stackless = True
    annotator = t.buildannotator()
    annotator.policy.allow_someobjects = False

    s_returnvar = annotator.build_types(fn, [s_list_of_strings])
    if not isinstance(s_returnvar, annmodel.SomeInteger):
        raise Exception, "this probably isn't going to work"
    t.buildrtyper().specialize()

    from pypy.translator.transform import insert_ll_stackcheck
    insert_ll_stackcheck(t)

#    if conftest.option.view:
#        t.view()
    return t
    
def run_stackless_function(fn):
    def entry_point(argv):
        r = fn()
        os.write(1, str(r)+'\n')
        return 0

    t = rtype_stackless_function(entry_point)

    cbuilder = CStandaloneBuilder(t, entry_point, config=t.config,
                                  gcpolicy=gc.BoehmGcPolicy)
    cbuilder.generate_source()
    if conftest.option.view:
        t.view()
    cbuilder.compile()
    res = cbuilder.cmdexec('')
    return int(res.strip())

def llinterp_stackless_function(fn, returntranslator=False,
                                assert_unwind=True):
    def wrapper(argv):
        return fn()
    t = rtype_stackless_function(wrapper)
    st = StacklessTransformer(t, wrapper, assert_unwind=assert_unwind)
    st.transform_all()
    if conftest.option.view:
        t.view()

    graph = graphof(t, st.slp_entry_point)
    r_list_of_strings = t.rtyper.getrepr(
        t.annotator.binding(graph.startblock.inputargs[0]))
    ll_list = r_list_of_strings.convert_const([''])
    interp = llinterp.LLInterpreter(t.rtyper)
    res = interp.eval_graph(graph, [ll_list])
    if returntranslator:
        return res, t
    else:
        return res
