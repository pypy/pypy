import py
import os
from pypy.translator.stackless.transform import StacklessTransformer
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.translator.c import gc
from pypy.rpython.memory.gctransform import varoftype
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import llinterp
from pypy.translator.translator import TranslationContext, graphof
from pypy.objspace.flow.model import checkgraph
from pypy.annotation import model as annmodel
from pypy.annotation.listdef import ListDef 
from pypy import conftest

## def test_frame_types():
##     st = StacklessTransfomer(None)

##     signed = varoftype(lltype.Signed)
##     ptr = varoftype(lltype.Ptr(lltype.GcStruct("S")))
##     addr = varoftype(llmemory.Address)
##     float = varoftype(lltype.Float)
##     longlong = varoftype(lltype.SignedLongLong)

##     ft4vars = st.frame_type_for_vars
    
##     s1 = ft4vars([signed])
##     assert 'header' in s1._flds
##     assert len(s1._flds) == 2

##     s2_1 = ft4vars([signed, ptr])
##     s2_2 = ft4vars([ptr, signed])

##     assert s2_1 is s2_2

from pypy.translator.stackless import code

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
    res = llinterp_stackless_function(fn)
    assert res == 21

def test_simple_transform_llinterp():
    def check(x):
        if x:
            raise code.UnwindException
    check.stackless_explicit = True
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
            raise code.UnwindException
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
            raise code.UnwindException # XXX or so
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
            raise code.UnwindException
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
            raise code.UnwindException
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
            raise code.UnwindException
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
            raise code.UnwindException
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
            raise code.UnwindException
    check.stackless_explicit = True
    def f():
        l = one()
        check(l)
        return len([x for x in range(l)])
    res = llinterp_stackless_function(f)
    assert res == 1
    

def rtype_stackless_function(fn):
    s_list_of_strings = annmodel.SomeList(ListDef(None, annmodel.SomeString()))
    s_list_of_strings.listdef.resize()
    t = TranslationContext()
    annotator = t.buildannotator()
    annotator.policy.allow_someobjects = False

    s_returnvar = annotator.build_types(fn, [s_list_of_strings])
    if not isinstance(s_returnvar, annmodel.SomeInteger):
        raise Exception, "this probably isn't going to work"
    t.buildrtyper().specialize()

    from pypy.translator.transform import insert_ll_stackcheck
    insert_ll_stackcheck(t)

    if conftest.option.view:
        t.view()
    return t
    
def run_stackless_function(fn):
    def entry_point(argv):
        r = fn()
        os.write(1, str(r)+'\n')
        return 0

    t = rtype_stackless_function(entry_point)

    cbuilder = CStandaloneBuilder(t, entry_point, gcpolicy=gc.BoehmGcPolicy)
    cbuilder.stackless = True
    cbuilder.generate_source()
    if conftest.option.view:
        t.view()
    cbuilder.compile()
    res = cbuilder.cmdexec('')
    return int(res.strip())

def llinterp_stackless_function(fn):
    def wrapper(argv):
        return fn()
    t = rtype_stackless_function(wrapper)
    st = StacklessTransformer(t, wrapper)
    st.transform_all()
    if conftest.option.view:
        t.view()

    graph = graphof(t, st.slp_entry_point)
    r_list_of_strings = t.rtyper.getrepr(
        t.annotator.binding(graph.startblock.inputargs[0]))
    ll_list = r_list_of_strings.convert_const([''])
    interp = llinterp.LLInterpreter(t.rtyper)
    res = interp.eval_graph(graph, [ll_list])
    return res
