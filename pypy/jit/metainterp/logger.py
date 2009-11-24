import os
from pypy.rlib.debug import have_debug_prints
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import Const, ConstInt, Box, \
     BoxInt, ConstAddr, ConstFloat, BoxFloat, AbstractFailDescr

class Logger(object):

    def __init__(self, metainterp_sd, guard_number=False):
        self.metainterp_sd = metainterp_sd
        self.ts = metainterp_sd.cpu.ts
        self.guard_number = guard_number

    def log_loop(self, inputargs, operations, number=0, type=None):
        if type is None:
            debug_start("jit-log-noopt-loop")
            self._log_operations(inputargs, operations)
            debug_stop("jit-log-noopt-loop")
        else:
            debug_start("jit-log-opt-loop")
            debug_print("# Loop", number, ":", type,
                        "with", len(operations), "ops")
            self._log_operations(inputargs, operations)
            debug_stop("jit-log-opt-loop")

    def log_bridge(self, inputargs, operations, number=-1):
        if number == -1:
            debug_start("jit-log-noopt-bridge")
            self._log_operations(inputargs, operations)
            debug_stop("jit-log-noopt-bridge")
        else:
            debug_start("jit-log-opt-bridge")
            debug_print("# bridge out of Guard", number,
                        "with", len(operations), "ops")
            self._log_operations(inputargs, operations)
            debug_stop("jit-log-opt-bridge")

    def repr_of_descr(self, descr):
        return descr.repr_of_descr()

    def repr_of_arg(self, memo, arg):
        try:
            mv = memo[arg]
        except KeyError:
            mv = len(memo)
            memo[arg] = mv
        if isinstance(arg, ConstInt):
            return str(arg.value)
        elif isinstance(arg, BoxInt):
            return 'i' + str(mv)
        elif isinstance(arg, self.ts.ConstRef):
            return 'ConstPtr(ptr' + str(mv) + ')'
        elif isinstance(arg, self.ts.BoxRef):
            return 'p' + str(mv)
        elif isinstance(arg, ConstFloat):
            return str(arg.value)
        elif isinstance(arg, BoxFloat):
            return 'f' + str(mv)
        elif isinstance(arg, self.ts.ConstAddr):
            addr = arg.getaddr(self.metainterp_sd.cpu)
            name = self.metainterp_sd.get_name_from_address(addr)
            if not name:
                name = 'cls' + str(mv)
            return 'ConstClass(' + name + ')'
        elif arg is None:
            return 'None'
        else:
            return '?'

    def _log_operations(self, inputargs, operations):
        if not have_debug_prints():
            return
        memo = {}
        if inputargs is not None:
            args = ", ".join([self.repr_of_arg(memo, arg) for arg in inputargs])
            debug_print('[' + args + ']')
        for i in range(len(operations)):
            op = operations[i]
            if op.opnum == rop.DEBUG_MERGE_POINT:
                loc = op.args[0]._get_str()
                debug_print("debug_merge_point('%s')" % (loc,))
                continue
            args = ", ".join([self.repr_of_arg(memo, arg) for arg in op.args])
            if op.result is not None:
                res = self.repr_of_arg(memo, op.result) + " = "
            else:
                res = ""
            is_guard = op.is_guard()
            if op.descr is not None:
                descr = op.descr
                if is_guard and self.guard_number:
                    index = self.metainterp_sd.cpu.get_fail_descr_number(descr)
                    r = "<Guard%d>" % index
                else:
                    r = self.repr_of_descr(descr)
                args += ', descr=' +  r
            if is_guard and op.fail_args is not None:
                fail_args = ' [' + ", ".join([self.repr_of_arg(memo, arg)
                                              for arg in op.fail_args]) + ']'
            else:
                fail_args = ''
            debug_print(res + op.getopname() +
                        '(' + args + ')' + fail_args)
