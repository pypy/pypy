import sys, operator, types, new, autopath
import pypy
from pypy.objspace.std import StdObjSpace
from pypy.objspace.trivial import TrivialObjSpace
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.pycode import PyCode
from pypy.interpreter import gateway

DONT_TRACK_BYTECODES = ["PRINT_ITEM", "PRINT_NEWLINE", "PRINT_EXPR", "PRINT_ITEM_TO", "PRINT_NEWLINE_TO"]


class TraceExecutionContext(ExecutionContext):        
    
    def bytecode_trace(self, frame):
        "Trace function called before each bytecode."
        self.space.notify_on_bytecode(frame)


class Tracer(object):
    def __init__(self, name, fn, space):
        self.fn = fn
        self.name = name
        self.space = space
        
    def __call__(self, cls, *args, **kwds):
        assert (not kwds)

        self.space.notify_on_operation(self.name, args)
        return self.fn(*args, **kwds)

    def __getattr__(self, name):
        return getattr(self.fn, name)


def Trace(spacecls = StdObjSpace):

    class TraceObjSpace(spacecls):
        full_exceptions = False
        
        def initialize(self):
            self.tracing = 0
            self.ignore_up_to_frame = None
            spacecls.initialize(self)
            method_names = [ii[0] for ii in ObjSpace.MethodTable]
            for key in method_names:
                if key in method_names:
                    item = getattr(self, key)
                    l = Tracer(key, item, self)
                    setattr(self, key, new.instancemethod(l, self, TraceObjSpace))

        def start_tracing(self):
            self.tracing = 1
            self.log_list = []

        def stop_tracing(self):
            self.tracing = 0 

        def createexecutioncontext(self):
            "Factory function for execution contexts."
            return TraceExecutionContext(self)

        def handle_default(self, frame, opcode, opname, oparg, ins_idx):
            return opcode, opname, "", ins_idx

        def handle_SET_LINENO(self, frame, opcode, opname, oparg, ins_idx):
            return opcode, opname, "%s" % oparg, ins_idx

        def handle_LOAD_CONST(self, frame, opcode, opname, oparg, ins_idx):
            return opcode, opname, "%s (%r)" % (oparg, frame.getconstant(oparg)), ins_idx

        def handle_LOAD_FAST(self, frame, opcode, opname, oparg, ins_idx):
            return opcode, opname, "%s (%s)" % (oparg, frame.getlocalvarname(oparg)), ins_idx

        def notify_on_bytecode(self, frame):
            if not self.tracing and self.ignore_up_to_frame is frame:
                self.tracing = 1
                self.ignore_up_to_frame = None
            if self.tracing:
                opcode, opname, oparg, ins_idx = frame.examineop()
                handle_method = getattr(self, "handle_%s" % opname, self.handle_default)
                
                opcode, opname, oparg, ins_idx = handle_method(frame, opcode, opname, oparg, ins_idx)
                self.log_list.append(((opcode, opname, oparg, ins_idx), []))
                if opname in DONT_TRACK_BYTECODES:
                    self.ignore_up_to_frame = frame
                    self.tracing = 0


        def notify_on_operation(self, name, args):
            if self.tracing:
                self.log_list[-1][1].append((name, args))
                

        def dump(self):
            return self.log_list

        def rdump(self):
            bytecodes = []
            res = []
            for bytecode, ops in self.log_list:
                bytecodes.append(bytecode)
                if ops:
                    op = ops.pop(0)
                    res.append((op, bytecodes))
                    bytecodes = []
                    for op in ops:
                        res.append((op, []))

            #the rest
            res.append((None, bytecodes))
            return res        

                    
    return TraceObjSpace()


Space = Trace

# ______________________________________________________________________
# End of trace.py


## if __name__ == "__main__":

    
##     s = Trace(TrivialObjSpace)
    
##     def a(b):
##         print "x"
##         if b > 2:
##             return b*2 
##         else:
##             return b

##     print run_function(s, a, 1)

##     print ">>>>>>"
##     for line in s.dump():
##         ((opcode, opname, arg, ins_idx), spaceops) = line
##         print ins_idx, opname, spaceops
##     print ">>>>>>"
##     #for line in s.rdump():
##     #    print line

##     #import dis
##     #dis.dis(a)
