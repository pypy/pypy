import py
from pypy.jit.metainterp.test import test_loop
from pypy.jit.backend.cli.test.test_basic import CliJitMixin


class TestLoop(CliJitMixin, test_loop.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_loop.py

    def skip(self):
        py.test.skip("works only after translation")

    test_loop_with_two_paths = skip
    test_interp_many_paths = skip
    test_interp_many_paths_2 = skip
    test_adapt_bridge_to_merge_point = skip
    test_outer_and_inner_loop = skip
    test_path_with_operations_not_from_start_2 = skip
    test_loop_unicode = skip
    test_loop_string = skip
    test_loop_with_delayed_setfield = skip
    
