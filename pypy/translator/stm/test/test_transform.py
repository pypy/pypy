from pypy.translator.stm.transform import STMTransformer
from pypy.translator.stm.transform import pre_insert_stm_writebarrier
from pypy.translator.translator import TranslationContext, graphof
from pypy.conftest import option
from pypy.objspace.flow.model import summary


def get_graph(func, sig):
    t = TranslationContext()
    t.buildannotator().build_types(func, sig)
    t.buildrtyper().specialize()
    if option.view:
        t.view()
    return graphof(t, func)


def test_pre_insert_stm_writebarrier():
    class X:
        pass
    class Y(X):
        pass
    class Z(X):
        pass
    def f1(n):
        if n > 5:
            x = Z()
        else:
            x = Y()
        x.n = n
        if n > 5:
            assert isinstance(x, Z)
            x.n = n + 2
            x.sub = n + 1
        x.n *= 2
    #
    graph = get_graph(f1, [int])
    pre_insert_stm_writebarrier(graph)
    if option.view:
        graph.show()
    # weak test: check that there are exactly two stm_writebarrier inserted.
    # one should be for 'x.n = n', and one should cover both field assignments
    # to the Z instance.
    sum = summary(graph)
    assert sum['stm_writebarrier'] == 3
