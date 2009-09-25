import os
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import Const, ConstInt, Box, \
     BoxInt, ConstAddr
from pypy.rlib.streamio import open_file_as_stream

class Logger(object):

    def __init__(self, ts):
        self.log_stream = None
        self.ts = ts

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

    def log_loop(self, inputargs, operations):
        self.log_operations(inputargs, operations, {})

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
        elif isinstance(arg, self.ts.ConstAddr):
            return 'ConstClass(cls' + str(mv) + ')'
        else:
            raise NotImplementedError

    def log_operations(self, inputargs, operations, memo, indent=0):
        if self.log_stream is None:
            return
        pre = " " * indent
        if inputargs is not None:
            args = ", ".join([self.repr_of_arg(memo, arg) for arg in inputargs])
            self.log_stream.write(pre + '[' + args + ']\n')
        for i in range(len(operations)):
            op = operations[i]
            if op.opnum == rop.DEBUG_MERGE_POINT:
                loc = op.args[0]._get_str()
                self.log_stream.write(pre + "debug_merge_point('%s')\n" % (loc,))
                continue
            args = ", ".join([self.repr_of_arg(memo, arg) for arg in op.args])
            if op.result is not None:
                res = self.repr_of_arg(memo, op.result) + " = "
            else:
                res = ""
            if op.descr is not None:
                args += ', descr=' + self.repr_of_descr(op.descr)
            self.log_stream.write(pre + res + op.getopname() +
                                  '(' + args + ')\n')
            if op.is_guard():
                self.log_operations(None, op.suboperations, memo,
                                    indent=indent+2)
        self.log_stream.flush()
