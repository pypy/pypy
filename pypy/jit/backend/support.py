import os
from pypy.rlib.objectmodel import compute_unique_id
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import Const, ConstInt, Box, ConstPtr, BoxPtr,\
     BoxInt, ConstAddr, BoxObj, ConstObj

class AbstractLogger(object):

    # is_oo = ...   ## need to be set by concrete classes
    
    def __init__(self):
        self._log_fd = -1

    def create_log(self):
        if self._log_fd != -1:
            return self._log_fd
        s = os.environ.get('PYPYJITLOG')
        if not s:
            return -1
        s += '.ops'
        try:
            flags = os.O_WRONLY|os.O_CREAT|os.O_TRUNC
            self._log_fd = os.open(s, flags, 0666)
        except OSError:
            os.write(2, "could not create log file\n")
            return -1
        return self._log_fd

    def repr_of_descr(self, descr):
        return ''

    def repr_of_arg(self, memo, arg):
        try:
            mv = memo[arg]
        except KeyError:
            mv = len(memo)
            memo[arg] = mv
        if isinstance(arg, ConstInt):
            return "ci(%d,%d)" % (mv, arg.value)
        elif isinstance(arg, BoxInt):
            return "bi(%d,%d)" % (mv, arg.value)
        elif not self.is_oo and isinstance(arg, ConstPtr):
            return "cp(%d,%d)" % (mv, arg.get_())
        elif not self.is_oo and isinstance(arg, BoxPtr):
            return "bp(%d,%d)" % (mv, arg.get_())
        elif not self.is_oo and isinstance(arg, ConstAddr):
            return "ca(%d,%d)" % (mv, arg.get_())
        elif self.is_oo and isinstance(arg, ConstObj):
            return "co(%d,%d)" % (mv, arg.get_())
        elif self.is_oo and isinstance(arg, BoxObj):
            return "bo(%d,%d)" % (mv, arg.get_())
        else:
            #raise NotImplementedError
            return "?%r" % (arg,)

    def eventually_log_operations(self, inputargs, operations, memo=None,
                                  myid=0, indent=0):
        if self._log_fd == -1:
            return
        pre = " " * indent
        if memo is None:
            memo = {}
        if inputargs is None:
            os.write(self._log_fd, pre + "BEGIN(%s)\n" % myid)
        else:
            args = ",".join([self.repr_of_arg(memo, arg) for arg in inputargs])
            os.write(self._log_fd, pre + "LOOP %s\n" % args)
        for i in range(len(operations)):
            op = operations[i]
            args = ",".join([self.repr_of_arg(memo, arg) for arg in op.args])
            if op.descr is not None:
                descr = self.repr_of_descr(op.descr)
                os.write(self._log_fd, pre + "%d:%s %s[%s]\n" %
                         (i, op.getopname(), args, descr))
            else:
                os.write(self._log_fd, pre + "%d:%s %s\n" %
                         (i, op.getopname(), args))
            if op.result is not None:
                os.write(self._log_fd, pre + "  => %s\n" %
                         self.repr_of_arg(memo, op.result))
            if op.is_guard():
                self.eventually_log_operations(None, op.suboperations, memo,
                                               indent=indent+2)
        if operations[-1].opnum == rop.JUMP:
            if operations[-1].jump_target is not None:
                jump_target = compute_unique_id(operations[-1].jump_target)
            else:
                # XXX hack for the annotator
                jump_target = 13
            os.write(self._log_fd, pre + 'JUMPTO:%s\n' % jump_target)
        if inputargs is None:
            os.write(self._log_fd, pre + "END\n")
        else:
            os.write(self._log_fd, pre + "LOOP END\n")

    def log_failure_recovery(self, gf, guard_index):
        if self._log_fd == -1:
            return
        return # XXX
        os.write(self._log_fd, 'xxxxxxxxxx\n')
        memo = {}
        reprs = []
        for j in range(len(gf.guard_op.liveboxes)):
            valuebox = gf.cpu.getvaluebox(gf.frame, gf.guard_op, j)
            reprs.append(self.repr_of_arg(memo, valuebox))
        jmp = gf.guard_op._jmp_from
        os.write(self._log_fd, "%d %d %s\n" % (guard_index, jmp,
                                               ",".join(reprs)))
        os.write(self._log_fd, 'xxxxxxxxxx\n')

    def log_call(self, valueboxes):
        if self._log_fd == -1:
            return
        return # XXX
        memo = {}
        args_s = ','.join([self.repr_of_arg(memo, box) for box in valueboxes])
        os.write(self._log_fd, "CALL\n")
        os.write(self._log_fd, "%s %s\n" % (name, args_s))
