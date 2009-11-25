import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_loop


class TestLoop(CliTranslatedJitMixin, test_loop.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py

    def skip(self):
        py.test.skip('in-progress')

    def test_interp_many_paths(self):
        pass # no chance to pass it after translation, because it passes
             # non-int arguments to the function
    
    def test_interp_many_paths_2(self):
        pass # see above

