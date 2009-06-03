
import py
from pypy.jit.metainterp.test.test_virtualizable import ImplicitVirtualizableTests
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin

class TestVirtualizable(Jit386Mixin, ImplicitVirtualizableTests):
    def test_pass_always_virtual_to_bridge(self):
        py.test.skip("Not implemented nonsense in patch_jump")

    def test_virtual_obj_on_always_virtual(self):
        py.test.skip("Widening to trash error")

    def test_virtual_obj_on_always_virtual_more_bridges(self):
        py.test.skip("Widening to trash error")
