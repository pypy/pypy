import py
import os
from pypy.translator.stackless.transform import StacklessTransfomer
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.rpython.memory.gctransform import varoftype
from pypy.rpython.lltypesystem import lltype, llmemory
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

def test_simple_transform():
    from pypy.translator.stackless.code import UnwindException
    def check(x):
        if x:
            raise UnwindException # XXX or so
    def g(x):
        check(x)
        return x + 1
    def example(x):
        return g(x) + 1
    res = run_stackless_function(example, example, g)
    assert res == "6"
    
def run_stackless_function(fn, *stacklessfuncs):
    def entry_point(argv):
        os.write(1, str(fn(len(argv)))+'\n')
        return 0

    s_list_of_strings = annmodel.SomeList(ListDef(None, annmodel.SomeString()))
    s_list_of_strings.listdef.resize()
    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()

    st = StacklessTransfomer(t)
    for func in stacklessfuncs: 
        graph = graphof(t, func)
        st.transform_graph(graph) 
        checkgraph(graph) 
    if conftest.option.view:
        t.view()

    cbuilder = CStandaloneBuilder(t, entry_point)
    cbuilder.generate_source()
    cbuilder.compile()
    return cbuilder.cmdexec('')
