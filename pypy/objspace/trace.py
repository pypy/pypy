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
        print "XXX %s, %s" % frame.examineop()

class Logger(object):
    def __init__(self, name, fn, printme):
        self.fn = fn
        self.name = name
        self.printme = printme
        
    def __call__(self, cls, *args, **kwds):
        print self.name
        #print "%s %s(%s, %s)" % (self.printme, , str(args), str(kwds)) 
        return self.fn(*args, **kwds)

    def __getattr__(self, name):
        return getattr(self.fn, name)

        
# ______________________________________________________________________

def Trace(spacecls = StdObjSpace):

    class TraceObjSpace(spacecls):
        full_exceptions = False
        
        def initialize(self):
            spacecls.initialize(self)

            method_names = [ii[0] for ii in ObjSpace.MethodTable]
            for key in method_names:
                if key in method_names:
                    item = getattr(self, key)
                    l = Logger(key, item, "class method")
                    #print l
                    setattr(self, key, new.instancemethod(l, self, TraceObjSpace))

        def createexecutioncontext(self):
            "Factory function for execution contexts."
            return TraceExecutionContext(self)


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
