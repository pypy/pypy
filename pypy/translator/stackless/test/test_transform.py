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

def test_simple_transform_llinterp():
    def check(x):
        if x:
            raise code.UnwindException
    check.stackless_explicit = True
    def g(x):
        check(x)
        return x + 1
    def example(x):
        return g(x) + 1
    res = llinterp_stackless_function(example)
    assert res == 3

def test_simple_transform_llinterp_float():
    def check(x):
        if x:
            raise code.UnwindException
    def g(x):
        check(x)
        return x + 0.125
    def example(x):
        return int((g(x) + 1)*1000.0)
    res = llinterp_stackless_function(example)
    assert res == 2125

def test_simple_transform_compiled():
    def check(x):
        if x:
            raise code.UnwindException # XXX or so
    def g(x):
        check(x)
        return x + 1
    def example(x):
        return g(x) + 1
    res = run_stackless_function(example)
    assert res.strip() == "3"

def test_protected_call():
    def check(x):
        if x:
            raise code.UnwindException
    def g(x):
        check(x)
        return x + 1
    def example(x):
        try:
            y = g(x)
        except Exception:
            y = -1
        return y + 1
    res = llinterp_stackless_function(example)
    assert res == 3
    res = run_stackless_function(example)
    assert res == "3"

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
    def example(x):
        y = h(x)
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
    def example(x):
        try:
            y = h(x)
        except KeyError:
            y = -1
        return y + 1
    res = llinterp_stackless_function(example)
    assert res == 0

def test_listcomp():
    def check(x):
        if x:
            raise code.UnwindException
    check.stackless_explicit = True
    def f(l):
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
    bk = annotator.bookkeeper
    # we want to make sure that the annotator knows what
    # code.UnwindException looks like very early on, because otherwise
    # it can get mutated during the annotation of the low level
    # helpers which can cause slp_main_loop to get re-annotated after
    # it is rtyped.  which is bad.
    unwind_def = bk.getuniqueclassdef(code.UnwindException)
    #unwind_def.generalize_attr('frame_top',
    #                           annmodel.SomePtr(lltype.Ptr(code.STATE_HEADER)))
    unwind_def.generalize_attr('frame_bottom',
                               annmodel.SomePtr(lltype.Ptr(code.STATE_HEADER)))
    
    s_returnvar = annotator.build_types(fn, [s_list_of_strings])
    if not isinstance(s_returnvar, annmodel.SomeInteger):
        raise Exception, "this probably isn't going to work"
    t.buildrtyper().specialize()

    if conftest.option.view:
        t.view()
    return t
    
def run_stackless_function(fn):
    def entry_point(argv):
        try:
            r = fn(len(argv))
        except code.UnwindException, u:
            code.slp_main_loop()
            r = code.global_state.retval_long
        os.write(1, str(r)+'\n')
        return 0
    entry_point.stackless_explicit = True

    t = rtype_stackless_function(entry_point)

    t.stacklesstransformer = StacklessTransformer(t)

    cbuilder = CStandaloneBuilder(t, entry_point)
    cbuilder.generate_source()
    if conftest.option.view:
        t.view()
    cbuilder.compile()
    return cbuilder.cmdexec('').strip()

def llinterp_stackless_function(fn):
    def entry_point(argv):
        try:
            r = fn(len(argv))
        except code.UnwindException, u:
            code.slp_main_loop()
            return code.global_state.retval_long
        return r
    entry_point.stackless_explicit = True

    t = rtype_stackless_function(entry_point)
    st = StacklessTransformer(t)
    st.transform_all()
    if conftest.option.view:
        t.view()

    r_list_of_strings = t.rtyper.getrepr(
        t.annotator.binding(graphof(t, entry_point).startblock.inputargs[0]))
    ll_list = r_list_of_strings.convert_const([''])
    interp = llinterp.LLInterpreter(t.rtyper)
    res = interp.eval_graph(graphof(t, entry_point), [ll_list])
    return res
