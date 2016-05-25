from rpython.jit.backend.arm.test.support import JitARMMixin
from rpython.jit.metainterp.test import test_compatible


class TestCompatible(JitARMMixin, test_compatible.TestCompatible):
    pass
