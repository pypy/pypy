# ______________________________________________________________________
import autopath
import sys, operator, types, new
import pypy
from pypy.objspace.std import StdObjSpace
from pypy.objspace.trivial import TrivialObjSpace
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.pycode import PyCode
debug = 0

class TraceExecutionContext(ExecutionContext):        
        
    def bytecode_trace(self, frame):
        "Trace function called before each bytecode."
        #print "XXX %s, %s" % frame.examineop()
        self.space.notify_on_bytecode(frame)

        
    def dump(self):
        bytecodes = self.list_of_bytecodes
        self.list_of_bytecodes = []
        return bytecodes
    
    

class Logger(object):
    def __init__(self, name, fn, space, printme):
        self.fn = fn
        self.name = name
        self.space = space
        self.printme = printme
        
    def __call__(self, cls, *args, **kwds):
        print self.name
        #print "%s %s(%s, %s)" % (self.printme, , str(args), str(kwds)) 
        self.space.notify_on_operation(self.name)
        return self.fn(*args, **kwds)

    def __getattr__(self, name):
        return getattr(self.fn, name)


class InteractiveLogger(Logger):
        
    def __call__(self, cls, *args, **kwds):
        res = Logger.__call__(self, cls, *args, **kwds)
        raw_input()
        return res
        
# ______________________________________________________________________

def Trace(spacecls = StdObjSpace, logger_cls = Logger):

    class TraceObjSpace(spacecls):
        full_exceptions = False
        
        def initialize(self):
            self.log_list = []
            self.current_frame = None
            spacecls.initialize(self)
            self.current_frame = None
            self.log_list = []
            method_names = [ii[0] for ii in ObjSpace.MethodTable]
            for key in method_names:
                if key in method_names:
                    item = getattr(self, key)
                    l = logger_cls(key, item, self, "class method")
                    setattr(self, key, new.instancemethod(l, self, TraceObjSpace))

        def createexecutioncontext(self):
            "Factory function for execution contexts."
            return TraceExecutionContext(self)


        def notify_on_bytecode(self, frame):
            if self.current_frame is None:
                self.current_frame = frame
            elif self.current_frame is frame:
                bytecode, name = frame.examineop()
                self.log_list.append((name, []))


        def notify_on_operation(self, name):
            self.log_list[-1][1].append(name)

        def dump(self):
            return self.log_list
        
    return TraceObjSpace()

Space = Trace
s = Trace(TrivialObjSpace)
#print dir(s)
# ______________________________________________________________________
# End of trace.py


def runx(space, func, *args):
    args_w = [space.wrap(ii) for ii in args]
    ec = space.getexecutioncontext()
    code = func.func_code
    code = PyCode()._from_code(code)
    w_globals = ec.make_standard_w_globals()  
    frame = code.create_frame(space, w_globals)
    frame.setfastscope(args_w)
    return frame.run()

if __name__ == "__main__":
    def a(b):
        print b
        return b+1

    print runx(s, a, 1)

    print ">>>>>>"
    print s.dump()
