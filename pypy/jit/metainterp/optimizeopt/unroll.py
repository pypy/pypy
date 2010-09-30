from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.compile import ResumeGuardDescr

class OptUnroll(Optimization):
    """Unroll the loop into two itterations. The first one will
    become the preamble or entry bridge (don't think there is a
    distinction anymore)"""
    
    def setup(self, virtuals):
        self.enabled = virtuals

    def propagate_forward(self, op):
        if not self.enabled:
            self.emit_operation(op)
            return

        if op.getopnum() == rop.JUMP:
            loop = self.optimizer.loop
            loop.preamble.operations = self.optimizer.newoperations
            self.optimizer.newoperations = []
            jump_args = op.getarglist()
            inputargs = self.inline(loop.preamble.operations + [op],
                                     loop.inputargs, jump_args)
            print "IN: ", inputargs
            loop.inputargs = inputargs
            jmp = ResOperation(rop.JUMP, loop.inputargs[:], None)
            jmp.setdescr(loop.token)
            loop.preamble.operations.append(jmp)
        else:
            self.emit_operation(op)

    def inline(self, loop_operations, loop_args, jump_args):
        argmap = {}
        assert len(loop_args) == len(jump_args)
        for i in range(len(loop_args)):
           argmap[loop_args[i]] = jump_args[i]

        print
        print
        print argmap

        for v in self.optimizer.values.values():
           v.fromstart = True

        inputargs = jump_args[:]
        for op in loop_operations:
            print "I:", op
            newop = op.clone()
            for i in range(op.numargs()):
                a = op.getarg(i)
                if not isinstance(a, Const):
                    newa = argmap[a]
                    newop.setarg(i, newa)
            if op.result:
                newop.result = op.result.clonebox()
                argmap[op.result] = newop.result
            descr = newop.getdescr()
            if isinstance(descr, ResumeGuardDescr):
                descr.rd_numb = None

            if newop.getopnum() == rop.JUMP:
                args = newop.getarglist()
                newop.initarglist(args + inputargs[len(args):])
                # FIXME: Assumes no virtuals
            print "N:", newop

            current = len(self.optimizer.newoperations)
            self.emit_operation(newop)
            for op in self.optimizer.newoperations[current:]:
                print "E:", op
                for a in op.getarglist():
                    if not isinstance(a, Const) and a in self.optimizer.values:
                        v = self.getvalue(a)
                        print "  testing ", a
                        if v.fromstart and a not in inputargs:
                            print "  ", a
                            inputargs.append(a)

        return inputargs

        

        
        
        
