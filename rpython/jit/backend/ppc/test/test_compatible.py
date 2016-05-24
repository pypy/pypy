from rpython.jit.backend.ppc.test.support import JitPPCMixin
from rpython.jit.metainterp.test import test_compatible


class TestCompatible(JitPPCMixin, test_compatible.TestCompatible):
    pass
