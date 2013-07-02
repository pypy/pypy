"""CompiledSTMTests, a support class for translated tests with STM"""

from rpython.translator.c.test.test_standalone import StandaloneTests


class CompiledSTMTests(StandaloneTests):

    def compile(self, entry_point, **kwds):
        from pypy.config.pypyoption import get_pypy_config
        self.config = get_pypy_config(translating=True)
        self.config.translation.gc = "stmgc"
        self.config.translation.stm = True
        #
        # Prevent the RaiseAnalyzer from just emitting "WARNING: Unknown
        # operation".  We want instead it to crash.
        from rpython.translator.backendopt.canraise import RaiseAnalyzer
        prev_setting = RaiseAnalyzer.fail_on_unknown_operation
        try:
            RaiseAnalyzer.fail_on_unknown_operation = True
            res = StandaloneTests.compile(self, entry_point, debug=True,
                                          **kwds)
        finally:
            RaiseAnalyzer.fail_on_unknown_operation = prev_setting
        return res
