from pypy.jit.hintannotator.test.test_annotator import hannotate, P_OOPSPEC
from pypy.jit.hintannotator.test.test_annotator import P_OOPSPEC_NOVIRTUAL


def test_hannotate_tl():
    from pypy.jit.tl import tl
    hannotate(tl.interp, [str, int, int], policy=P_OOPSPEC)

def test_hannotate_tl_novirtual():
    from pypy.jit.tl import tl
    hannotate(tl.interp, [str, int, int], policy=P_OOPSPEC_NOVIRTUAL)

def test_hannotate_tlr_novirtual():
    from pypy.jit.tl import tlr
    hannotate(tlr.interpret, [str, int], policy=P_OOPSPEC_NOVIRTUAL)

def test_hannotate_tlc_novirtual():
    from pypy.jit.tl import tlc
    hannotate(tlc.interp_without_call, [str, int, int],
              policy=P_OOPSPEC_NOVIRTUAL, backendoptimize=True)
