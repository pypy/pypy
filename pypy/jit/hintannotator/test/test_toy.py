import py
from pypy.jit.hintannotator.test.test_annotator import AbstractAnnotatorTest
from pypy.jit.hintannotator.test.test_annotator import P_OOPSPEC, P_OOPSPEC_NOVIRTUAL

class BaseToyTest(AbstractAnnotatorTest):
    def test_hannotate_tl(self):
        from pypy.jit.tl import tl
        self.hannotate(tl.interp, [str, int, int], policy=P_OOPSPEC)

    def test_hannotate_tl_novirtual(self):
        from pypy.jit.tl import tl
        self.hannotate(tl.interp, [str, int, int], policy=P_OOPSPEC_NOVIRTUAL)

    def test_hannotate_tlr_novirtual(self):
        from pypy.jit.tl import tlr
        self.hannotate(tlr.interpret, [str, int], policy=P_OOPSPEC_NOVIRTUAL)

    def test_hannotate_tlc_novirtual(self):
        from pypy.jit.tl import tlc
        self.hannotate(tlc.interp_without_call, [str, int, int],
                       policy=P_OOPSPEC_NOVIRTUAL, backendoptimize=True)

class TestLLType(BaseToyTest):
    type_system = 'lltype'

class TestOOType(BaseToyTest):
    type_system = 'ootype'

    def test_hannotate_tl(self):
        py.test.skip('fixme? (This policy is not relevant for now)')
