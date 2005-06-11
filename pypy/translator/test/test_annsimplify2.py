from pypy.annotation.policy import AnnotatorPolicy
from pypy.translator.annrpython import RPythonAnnotator
from pypy.objspace.flow import model as flowmodel

def test_simplify_spec():
    def g(*args):
        pass
    def f():
        g(1,2)
        g(1,2,3)
        g()
    a = RPythonAnnotator(policy=AnnotatorPolicy())
    s = a.build_types(f,[])
    calls = []
    for block in a.annotated:
        for op in block.operations:
            if op.opname == 'simple_call' and op.args[0] == flowmodel.Constant(g):
                calls.append(op)
    assert len(calls) == 3
    a.simplify()
    spec_gs = [op.args[0].value for op in calls]
    assert len(spec_gs) == 3
    assert g not in spec_gs
    assert spec_gs[0] != spec_gs[1]
    assert spec_gs[0] != spec_gs[2]
    assert spec_gs[1] != spec_gs[2]
    a.simplify()
    assert spec_gs == [op.args[0].value for op in calls] # idempotent

