from pypy.translator.backendopt.ssa import *
from pypy.translator.translator import Translator
from pypy.objspace.flow.model import flatten, Block


def test_data_flow_families():
    def snippet_fn(xx, yy):
        while yy > 0:
            if 0 < xx:
                yy = yy - xx
            else:
                yy = yy + xx
        return yy
    t = Translator(snippet_fn)
    graph = t.getflowgraph()
    operations = []
    for block in flatten(graph):
        if isinstance(block, Block):
            operations += block.operations

    variable_families = data_flow_families(graph)

    # we expect to find xx only once:
    v_xx = variable_families.find_rep(graph.getargs()[0])
    found = 0
    for op in operations:
        if op.opname in ('add', 'sub', 'lt'):
            assert variable_families.find_rep(op.args[1]) == v_xx
            found += 1
    assert found == 3


def test_SSI_to_SSA():
    def snippet_fn(v1, v2, v3):
        if v1:                             # v4 = is_true(v1)
            while v3:                      # v5 = is_true(v3)
                pass
            passed_over = 0
        else:
            v6 = snippet_fn(v3, v2, v1)    # v6 = simple_call(v3, v2, v1)
            passed_over = v6
        v7 = passed_over                   # v7 = inputarg
        return v7+v1                       # v8 = add(v7, v1)

    t = Translator(snippet_fn)
    SSI_to_SSA(t.getflowgraph())
    allvars = []
    for block in flatten(t.getflowgraph()):
        if isinstance(block, Block):
            allvars += [v.name for v in block.getvariables()]
    # see comments above for where the 8 remaining variables are expected to be
    assert len(dict.fromkeys(allvars)) == 8
