import os
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import Const, ConstInt, Box, \
     BoxInt, ConstAddr, ConstFloat, BoxFloat, AbstractFailDescr
from pypy.rlib.streamio import open_file_as_stream

class Logger(object):

    def __init__(self, ts, guard_number=False):
        self.log_stream = None
        self.ts = ts
        self.guard_number=guard_number

    def create_log(self, extension='.ops'):
        if self.log_stream is not None:
            return self.log_stream        
        s = os.environ.get('PYPYJITLOG')
        if not s:
            return None
        s += extension
        try:
            self.log_stream = open_file_as_stream(s, 'w')
        except OSError:
            os.write(2, "could not create log file\n")
            return None
        return self.log_stream

    def log_loop(self, inputargs, operations, number=0, type=None):
        if self.log_stream is None:
            return
        if type is not None:
            self.log_stream.write("# Loop%d (%s), %d ops\n" % (number,
                                                              type,
                                                              len(operations)))
        self._log_operations(inputargs, operations, {})

    def log_bridge(self, inputargs, operations, number=-1):
        if self.log_stream is None:
            return
        if number != -1:
            self.log_stream.write("# bridge out of Guard%d, %d ops\n" % (number,
                                                               len(operations)))
        self._log_operations(inputargs, operations, {})
        

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
            return 'ConstClass(cls' + str(mv) + ')'
        else:
            return '?'

    def _log_operations(self, inputargs, operations, memo):
        if inputargs is not None:
            args = ", ".join([self.repr_of_arg(memo, arg) for arg in inputargs])
            self.log_stream.write('[' + args + ']\n')
        for i in range(len(operations)):
            op = operations[i]
            if op.opnum == rop.DEBUG_MERGE_POINT:
                loc = op.args[0]._get_str()
                self.log_stream.write("debug_merge_point('%s')\n" % (loc,))
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
                    assert isinstance(descr, AbstractFailDescr)
                    r = "<Guard%d>" % descr.get_index()
                else:
                    r = self.repr_of_descr(descr)
                args += ', descr=' +  r
            if is_guard and op.fail_args is not None:
                fail_args = ' [' + ", ".join([self.repr_of_arg(memo, arg)
                                              for arg in op.fail_args]) + ']'
            else:
                fail_args = ''
            self.log_stream.write(res + op.getopname() +
                                  '(' + args + ')' + fail_args + '\n')
        self.log_stream.flush()
