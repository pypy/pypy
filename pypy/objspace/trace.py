# ______________________________________________________________________
import autopath
import sys, operator, types, new
import pypy
from pypy.objspace.std import StdObjSpace
from pypy.objspace.trivial import TrivialObjSpace
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.pycode import PyCode
from pypy.interpreter import gateway
debug = 0

class TraceExecutionContext(ExecutionContext):        
        
    def bytecode_trace(self, frame):
        "Trace function called before each bytecode."
        #print "XXX %s, %s" % frame.examineop()
        self.space.notify_on_bytecode(frame)

class Logger(object):
    def __init__(self, name, fn, space, printme):
        self.fn = fn
        self.name = name
        self.space = space
        self.printme = printme
        
    def __call__(self, cls, *args, **kwds):
        assert (not kwds)

        #print self.name
        #print "%s %s(%s, %s)" % (self.printme, , str(args), str(kwds)) 
        self.space.notify_on_operation(self.name, None)
        return self.fn(*args, **kwds)

    def __getattr__(self, name):
        return getattr(self.fn, name)


## XXX Interaction not in scope (yet)
## class InteractiveLogger(Logger):
        
##     def __call__(self, cls, *args, **kwds):
##         res = Logger.__call__(self, cls, *args, **kwds)
##         raw_input()
##         return res
        
# ______________________________________________________________________

def Trace(spacecls = StdObjSpace, logger_cls = Logger):

    class TraceObjSpace(spacecls):
        full_exceptions = False
        
        def initialize(self):
            self.tracing = 0
            spacecls.initialize(self)
            method_names = [ii[0] for ii in ObjSpace.MethodTable]
            for key in method_names:
                if key in method_names:
                    item = getattr(self, key)
                    l = logger_cls(key, item, self, "class method")
                    setattr(self, key, new.instancemethod(l, self, TraceObjSpace))

        def start_tracing(self):
            self.tracing = 1
            self.log_list = []

        def stop_tracing(self):
            self.tracing = 0 

        def createexecutioncontext(self):
            "Factory function for execution contexts."
            return TraceExecutionContext(self)


        def notify_on_bytecode(self, frame):
            if self.tracing:
                opcode, opname = frame.examineop()
                self.log_list.append((opname, []))


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
#s = Trace(TrivialObjSpace)
s = Trace()
# ______________________________________________________________________
# End of trace.py

def add_func(space, func, w_globals):
    """ Add a function to globals. """
    func_name = func.func_name
    w_func_name = space.wrap(func_name)
    w_func = space.wrap(func)
    space.setitem(w_globals, w_func_name, w_func)

def run_function(space, func, *args):
    # Get execution context and globals
    ec = space.getexecutioncontext()
    w_globals = ec.make_standard_w_globals()

    # Add the function to globals
    add_func(space, func, w_globals)

    # Create wrapped args
    args_w = [space.wrap(ii) for ii in args]
    code = func.func_code
    code = PyCode()._from_code(code)
    # Create frame
    frame = code.create_frame(space, w_globals)
    frame.setfastscope(args_w)
    
    # start/stop tracing while running frame
    space.start_tracing()
    res = frame.run()
    space.stop_tracing()

    return res


if __name__ == "__main__":
    
    def a(b):
        if b > 0:
            return a(b-1)
        else:
            return b

    print run_function(s, a, 3)

    print ">>>>>>"
    for line in s.dump():
        print line
    print ">>>>>>"
    for line in s.rdump():
        print line
