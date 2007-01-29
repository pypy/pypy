from pypy.jit.codegen.i386.test.test_genc_portal import I386PortalTestMixin
from pypy.jit.timeshifter.test import test_virtualizable


class TestVirtualizableExplicit(I386PortalTestMixin,
                                test_virtualizable.TestVirtualizableExplicit):
    pass

class TestVirtualizableImplicit(I386PortalTestMixin,
                                test_virtualizable.TestVirtualizableImplicit):
    pass

# for the individual tests see
# ====> ../../../timeshifter/test/test_virtualizable.py
