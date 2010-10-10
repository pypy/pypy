from pypy.jit.metainterp.optimizeopt.optimizer import *
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.compile import ResumeGuardDescr
from pypy.jit.metainterp.resume import Snapshot

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
            print '\n'.join([str(o) for o in loop.preamble.operations])
            self.optimizer.newoperations = []
            jump_args = op.getarglist()
            op.initarglist([])
            inputargs = self.inline(loop.operations,
                                    #loop.preamble.operations + [op],
                                    loop.inputargs, jump_args)
            loop.inputargs = inputargs
            jmp = ResOperation(rop.JUMP, loop.inputargs[:], None)
            jmp.setdescr(loop.token)
            loop.preamble.operations.append(jmp)
        else:
            self.emit_operation(op)

    def inline(self, loop_operations, loop_args, jump_args):
        self.argmap = argmap = {}
        assert len(loop_args) == len(jump_args)
        for i in range(len(loop_args)):
           argmap[loop_args[i]] = jump_args[i]

        for v in self.optimizer.values.values():
            if not v.is_constant() and v.box:
                v.fromstart = True

        self.snapshot_map ={None: None}
        
        inputargs = []
        for arg in jump_args:
            for a in self.getvalue(arg).get_forced_boxes():
                if not isinstance(a, Const):
                    inputargs.append(a)
        print "Inputargs: ", inputargs

        for op in loop_operations:
            #import pdb; pdb.set_trace()
            newop = op.clone()
            newop.initarglist([self.inline_arg(a) for a in newop.getarglist()])
            if op.result:
                newop.result = op.result.clonebox()
                argmap[op.result] = newop.result
            descr = newop.getdescr()
            if isinstance(descr, ResumeGuardDescr):
                op.getdescr().rd_snapshot = None #FIXME: In the right place?
                descr.rd_numb = None
                descr.rd_snapshot = self.inline_snapshot(descr.rd_snapshot)
                
            if newop.getopnum() == rop.JUMP:
                args = []
                #for arg in newop.getarglist():
                for arg in [argmap[a] for a in inputargs]:
                    args.extend(self.getvalue(arg).get_forced_boxes())
                newop.initarglist(args + inputargs[len(args):])

            print "P: ", newop
            current = len(self.optimizer.newoperations)
            self.emit_operation(newop)

            for op in self.optimizer.newoperations[current:]:
                print "E: ", op
                if op.is_guard():
                    op.getdescr().rd_snapshot = None #FIXME: In the right place?
                args = op.getarglist()
                if op.is_guard():
                    args = args + op.getfailargs()
                for a in args:
                    if not isinstance(a, Const) and a in self.optimizer.values:
                        v = self.getvalue(a)
                        if v.fromstart and a not in inputargs:
                            print "Arg: ", a
                            inputargs.append(a)
                            if op.getopnum() == rop.JUMP:
                                op.initarglist(op.getarglist() + [argmap[a]])

        return inputargs

    def inline_arg(self, arg):
        if isinstance(arg, Const):
            return arg
        return self.argmap[arg]

    def inline_snapshot(self, snapshot):
        if snapshot in self.snapshot_map:
            return self.snapshot_map[snapshot]
        boxes = []
        for a in snapshot.boxes:
            if isinstance(a, Const):
                boxes.append(a)
            else:
                boxes.append(self.inline_arg(a))
        return Snapshot(self.inline_snapshot(snapshot.prev), boxes)
    

        
        
        
