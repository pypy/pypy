# ______________________________________________________________________
import autopath
import sys, operator, types, new
import pypy
from pypy.objspace.std import StdObjSpace
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.pycode import PyCode
debug = 0

class Logger(object):
    def __init__(self, fn, printme):
        self.fn = fn
        self.printme = printme
        
    def __call__(self, cls, *args, **kwds):
        print "%s (%s, %s)" % (self.printme, str(args), str(kwds)) 
        return self.fn(*args, **kwds)

        
# ______________________________________________________________________
class TraceObjSpace(StdObjSpace):
    full_exceptions = False
    
    def initialize(self):
        space = StdObjSpace()
        self.space = space
        for key, item in space.__dict__.items():
            if not callable(item):
                print "key: %s" % key
                setattr(self, key, item)
            else:
                l = Logger(item, "instance method")
                print l
                setattr(self, key, new.instancemethod(l, self, TraceObjSpace))

        for key in space.__class__.__dict__.keys():
            item = getattr(space, key)
            if callable(item) and not key.startswith('__'):
                l = Logger(item, "class method")
                print l
                setattr(self, key, new.instancemethod(l, self, TraceObjSpace))

    def runx(self, func, *args):
        globals = {}
            
        w_globals = self.wrap(globals) 
        args_w = [self.wrap(ii) for ii in args]

        ec = self.getexecutioncontext()

        code = func.func_code
        code = PyCode()._from_code(code)

        frame = code.create_frame(space, w_globals)
        frame.setfastscope(args_w)
        
        return frame.run()
        

Space = TraceObjSpace
s = Space()
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
