import py
from pypy.jit.metainterp.test import test_exception
from pypy.jit.backend.cli.test.test_basic import CliJitMixin


class TestException(CliJitMixin, test_exception.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_exception.py

    def skip(self):
        py.test.skip("works only after translation")

    test_simple = skip
    test_bridge_from_guard_exception = skip
    test_bridge_from_guard_no_exception = skip
    test_four_levels_checks = skip
    test_exception_from_outside = skip
    test_exception_from_outside_2 = skip
    test_exception_two_cases = skip
    test_exception_two_cases_2 = skip
    test_exception_four_cases = skip
    test_exception_later = skip
    test_exception_and_then_no_exception = skip
    test_raise_through = skip
    test_raise_through_wrong_exc = skip
    test_raise_through_wrong_exc_2 = skip
    test_bridge_from_interpreter_exc = skip
    test_bridge_from_interpreter_exc_2 = skip
