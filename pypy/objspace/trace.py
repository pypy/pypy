# ______________________________________________________________________
import autopath
import sys, operator, types, new
import pypy
from pypy.objspace.std import StdObjSpace
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.pycode import PyCode
debug = 0

class Logger(object):
    def __init__(self, name, fn, printme):
        self.fn = fn
        self.name = name
        self.printme = printme
        
    def __call__(self, cls, *args, **kwds):
        print self.name
        #print "%s %s(%s, %s)" % (self.printme, , str(args), str(kwds)) 
        return self.fn(*args, **kwds)

        
# ______________________________________________________________________

def Trace(spacecls = StdObjSpace):

    class TraceObjSpace(spacecls):
        
        def initialize(self):
            self.space = spacecls()

            method_names = [ii[0] for ii in ObjSpace.MethodTable]
            for key in method_names:
                if key in method_names:
                    item = getattr(self.space, key)
                    l = Logger(key, item, "class method")
                    setattr(self, key, new.instancemethod(l, self, TraceObjSpace))

    return TraceObjSpace()


s = Trace()
print dir(s)
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
        return b+1

    print runx(s, a, 1)
