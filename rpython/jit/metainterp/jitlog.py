from rpython.rlib.rvmprof.rvmprof import cintf

class VMProfJitLogger(object):

    MARK_BLOCK_ASM = 0x10

    MARK_INPUT_ARGS = 0x11
    MARK_RESOP = 0x12

    MARK_RESOP_META = 0x13

    def __init__(self):
        self.cintf = cintf.setup()

    def setup_once(self):
        self.cintf.jitlog_try_init_using_env()
        if self.cintf.jitlog_filter(0x0):
            return
        self.cintf.jitlog_write_marker(MARK_RESOP_META);
        count = len(resoperation.opname)
        self.cintf.jitlog_write_int(count)
        for opnum, opname in resoperation.opname.items():
            self.cintf.write_marker(opnum)
            self.cintf.write_string(opname)

    def log_trace(self, tag, args, ops,
                  faildescr=None, ops_offset={}):
        if self.cintf.jitlog_filter(tag):
            return
        assert isinstance(tag, int)
        self.cintf.jitlog_write_marker(tag);

        # input args
        self.cintf.jitlog_write_marker(MARK_INPUT_ARGS);
        str_args = [arg.repr_short(arg._repr_memo) for arg in args]
        self.cintf.jitlog_write_string(','.join(str_args))

        self.cintf.jitlog_write_int(len(ops))
        for i,op in enumerate(ops):
            self.cintf.jitlog_write_marker(MARK_RESOP)
            self.cintf.jitlog_write_marker(op.getopnum())
            str_args = [arg.repr_short(arg._repr_memo) for arg in op.getarglist()]
            descr = op.getdescr()
            if descr:
                str_args += ['descr='+descr]
            self.cintf.jitlog_write_string(','.join(str_args))
