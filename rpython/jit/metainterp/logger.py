from rpython.jit.metainterp.history import (ConstInt, BoxInt, ConstFloat,
    BoxFloat, TargetToken)
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.debug import (have_debug_prints, debug_start, debug_stop,
    debug_print)
from rpython.rlib.objectmodel import we_are_translated, compute_unique_id
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi


class Logger(object):
    def __init__(self, metainterp_sd, guard_number=False):
        self.metainterp_sd = metainterp_sd
        self.guard_number = guard_number

    def log_loop(self, inputargs, operations, number=0, type=None, ops_offset=None, name=''):
        if type is None:
            debug_start("jit-log-noopt-loop")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-noopt-loop")
        elif type == "rewritten":
            debug_start("jit-log-rewritten-loop")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-rewritten-loop")
        elif number == -2:
            debug_start("jit-log-compiling-loop")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-compiling-loop")
        else:
            debug_start("jit-log-opt-loop")
            debug_print("# Loop", number, '(%s)' % name, ":", type,
                        "with", len(operations), "ops")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-opt-loop")
        return logops

    def log_bridge(self, inputargs, operations, extra=None,
                   descr=None, ops_offset=None):
        if extra == "noopt":
            debug_start("jit-log-noopt-bridge")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-noopt-bridge")
        elif extra == "rewritten":
            debug_start("jit-log-rewritten-bridge")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-rewritten-bridge")            
        elif extra == "compiling":
            debug_start("jit-log-compiling-bridge")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-compiling-bridge")
        else:
            debug_start("jit-log-opt-bridge")
            debug_print("# bridge out of Guard",
                        "0x%x" % compute_unique_id(descr),
                        "with", len(operations), "ops")
            logops = self._log_operations(inputargs, operations, ops_offset)
            debug_stop("jit-log-opt-bridge")
        return logops

    def log_short_preamble(self, inputargs, operations):
        debug_start("jit-log-short-preamble")
        logops = self._log_operations(inputargs, operations, ops_offset=None)
        debug_stop("jit-log-short-preamble")
        return logops

    def _log_operations(self, inputargs, operations, ops_offset):
        if not have_debug_prints():
            return None
        logops = self._make_log_operations()
        logops._log_operations(inputargs, operations, ops_offset)
        return logops

    def _make_log_operations(self):
        return LogOperations(self.metainterp_sd, self.guard_number)

    def repr_of_resop(self, op):
        return LogOperations(self.metainterp_sd, self.guard_number).repr_of_resop(op)


class LogOperations(object):
    """
    ResOperation logger.  Each instance contains a memo giving numbers
    to boxes, and is typically used to log a single loop.
    """
    def __init__(self, metainterp_sd, guard_number):
        self.metainterp_sd = metainterp_sd
        self.ts = metainterp_sd.cpu.ts
        self.guard_number = guard_number
        self.memo = {}

    def repr_of_descr(self, descr):
        return descr.repr_of_descr()

    def repr_of_arg(self, arg):
        try:
            mv = self.memo[arg]
        except KeyError:
            mv = len(self.memo)
            self.memo[arg] = mv
        if isinstance(arg, ConstInt):
            if int_could_be_an_address(arg.value):
                addr = arg.getaddr()
                name = self.metainterp_sd.get_name_from_address(addr)
                if name:
                    return 'ConstClass(' + name + ')'
            return str(arg.value)
        elif isinstance(arg, BoxInt):
            return 'i' + str(mv)
        elif isinstance(arg, self.ts.ConstRef):
            if arg.value:
                return 'ConstPtr(ptr' + str(mv) + ')'
            return 'ConstPtr(null)'
        elif isinstance(arg, self.ts.BoxRef):
            return 'p' + str(mv)
        elif isinstance(arg, ConstFloat):
            return str(arg.getfloat())
        elif isinstance(arg, BoxFloat):
            return 'f' + str(mv)
        elif arg is None:
            return 'None'
        else:
            return '?'

    def repr_of_resop(self, op, ops_offset=None):
        if op.getopnum() == rop.DEBUG_MERGE_POINT:
            jd_sd = self.metainterp_sd.jitdrivers_sd[op.getarg(0).getint()]
            s = jd_sd.warmstate.get_location_str(op.getarglist()[3:])
            s = s.replace(',', '.') # we use comma for argument splitting
            return "debug_merge_point(%d, %d, '%s')" % (op.getarg(1).getint(), op.getarg(2).getint(), s)
        if ops_offset is None:
            offset = -1
        else:
            offset = ops_offset.get(op, -1)
        if offset == -1:
            s_offset = ""
        else:
            s_offset = "+%d: " % offset
        args = ", ".join([self.repr_of_arg(op.getarg(i)) for i in range(op.numargs())])

        if op.result is not None:
            res = self.repr_of_arg(op.result) + " = "
        else:
            res = ""
        is_guard = op.is_guard()
        if op.getdescr() is not None:
            descr = op.getdescr()
            if is_guard and self.guard_number:
                hash = compute_unique_id(descr)
                r = "<Guard0x%x>" % hash
            else:
                r = self.repr_of_descr(descr)
            if args:
                args += ', descr=' + r
            else:
                args = "descr=" + r
        if is_guard and op.getfailargs() is not None:
            fail_args = ' [' + ", ".join([self.repr_of_arg(arg)
                                          for arg in op.getfailargs()]) + ']'
        else:
            fail_args = ''
        return s_offset + res + op.getopname() + '(' + args + ')' + fail_args

    def _log_inputarg_setup_ops(self, op):
        target_token = op.getdescr()
        if isinstance(target_token, TargetToken):
            if target_token.exported_state:
                for op in target_token.exported_state.inputarg_setup_ops:
                    debug_print('    ' + self.repr_of_resop(op))

    def _log_operations(self, inputargs, operations, ops_offset):
        if not have_debug_prints():
            return
        if ops_offset is None:
            ops_offset = {}
        if inputargs is not None:
            args = ", ".join([self.repr_of_arg(arg) for arg in inputargs])
            debug_print('[' + args + ']')
        for i in range(len(operations)):
            op = operations[i]
            debug_print(self.repr_of_resop(operations[i], ops_offset))
            if op.getopnum() == rop.LABEL:
                self._log_inputarg_setup_ops(op)
        if ops_offset and None in ops_offset:
            offset = ops_offset[None]
            debug_print("+%d: --end of the loop--" % offset)


def int_could_be_an_address(x):
    if we_are_translated():
        x = rffi.cast(lltype.Signed, x)       # force it
        return not (-32768 <= x <= 32767)
    else:
        return isinstance(x, llmemory.AddressAsInt)
