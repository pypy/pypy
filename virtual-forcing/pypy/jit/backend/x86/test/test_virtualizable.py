
import py
from pypy.jit.metainterp.test.test_virtualizable import ImplicitVirtualizableTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestVirtualizable(Jit386Mixin, ImplicitVirtualizableTests):
    def test_blackhole_should_not_reenter(self):
        py.test.skip("Assertion error & llinterp mess")
