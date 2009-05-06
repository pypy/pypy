import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_send


class TestSend(CliTranslatedJitMixin, test_send.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_send.py

    def skip(self):
        py.test.skip('in-progress')

    test_send_to_single_target_method = skip
    test_oosend_base = skip
    test_three_receivers = skip
    test_oosend_different_initial_class = skip
    test_indirect_call_unknown_object_1 = skip
    test_three_cases = skip
    test_three_classes = skip
    test_recursive_call_to_portal_from_blackhole = skip
    test_residual_oosend = skip
