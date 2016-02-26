from rpython.rlib.rvmprof.rvmprof import cintf

class VMProfJitLogger(object):
    def __init__(self):
        self.cintf = cintf.setup()

    def _ensure_init(self):
        self.cintf.jitlog_try_init_using_env()

        self.cintf.write_marker(BinaryJitLogger.JIT_META_MARKER)
        count = len(resoperation.opname)
        assert count < 256
        self.cintf.write_marker(count)
        for opnum, opname in resoperation.opname.items():
            self.cintf.write_byte(opnum)
            self.cintf.write_string(opnum)

    def log_loop(self, operations):
        pass

    def _log_resoperation(self, op):
        pass
