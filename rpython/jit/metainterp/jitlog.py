from rpython.rlib.rvmprof.rvmprof import cintf
from rpython.jit.metainterp import resoperation as resoperations
import struct

class VMProfJitLogger(object):

    MARK_TRACED = 0x10
    MARK_ASM = 0x11

    MARK_INPUT_ARGS = 0x12
    MARK_RESOP = 0x13

    MARK_RESOP_META = 0x14
    MARK_RESOP = 0x15

    def __init__(self):
        self.cintf = cintf.setup()

    def setup_once(self):
        self.cintf.jitlog_try_init_using_env()
        if self.cintf.jitlog_filter(0x0):
            return
        count = len(resoperations.opname)
        mark = VMProfJitLogger.MARK_RESOP_META
        for opnum, opname in resoperations.opname.items():
            line = struct.pack(">h", opnum) + opname.lower()
            self.write_marked(mark, line)

    def teardown(self):
        self.cintf.jitlog_teardown()

    def write_marked(self, mark, line):
        self.cintf.jitlog_write_marked(mark, line, len(line))

    def log_trace(self, tag, args, ops,
                  faildescr=None, ops_offset={}):
        if self.cintf.jitlog_filter(tag):
            return
        assert isinstance(tag, int)

        # input args
        str_args = [arg.repr_short(arg._repr_memo) for arg in args]
        self.write_marked(self.MARK_INPUT_ARGS, ','.join(str_args))

        for i,op in enumerate(ops):
            str_args = [arg.repr_short(arg._repr_memo) for arg in op.getarglist()]
            descr = op.getdescr()
            if descr:
                str_args += ['descr='+descr]
            self.write_marked(self.MARK_RESOP, ','.join(args))
