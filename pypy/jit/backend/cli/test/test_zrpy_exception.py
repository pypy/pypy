import py
from pypy.jit.backend.cli.test.test_zrpy_basic import CliTranslatedJitMixin
from pypy.jit.metainterp.test import test_exception


class TestException(CliTranslatedJitMixin, test_exception.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_exception.py

    def skip_loop(self):
        py.test.skip('jump across loops not implemented yet')

    def skip(self):
        py.test.skip('in-progress')

    test_bridge_from_guard_exception = skip_loop
    
    test_exception_from_outside_2 = skip
    test_exception_two_cases = skip
    test_exception_two_cases_2 = skip
    test_exception_four_cases = skip
    test_exception_later = skip
    test_exception_and_then_no_exception = skip
    test_raise_through_wrong_exc_2 = skip
    test_int_ovf = skip
    test_int_lshift_ovf = skip
    test_bridge_from_interpreter_exc = skip
    test_bridge_from_interpreter_exc_2 = skip
