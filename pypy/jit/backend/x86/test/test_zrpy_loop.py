import py
from pypy.jit.metainterp.test.test_loop import LoopTest
from pypy.jit.backend.x86.test.test_zrpy_slist import Jit386Mixin

class TestLoop(Jit386Mixin, LoopTest):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py

    def test_interp_many_paths(self):
        py.test.skip('not supported: pointer as argument')

    def test_interp_many_paths_2(self):
        py.test.skip('not supported: pointer as argument')
