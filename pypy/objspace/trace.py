# ______________________________________________________________________
import autopath
import sys, operator, types
import pypy
from pypy.objspace.std import StdObjSpace
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.pycode import PyCode
debug = 0

# ______________________________________________________________________
class TraceObjSpace(ObjSpace):
    full_exceptions = False
    
    def initialize(self):
        space = StdObjSpace()
        for key, item in space.__dict__.items():
            if not callable(item):
                setattr(self, key, item)
            else:
                def logger(*args, **kwargs):
                    print "XXX"
                    return item(*args, **kwargs)
                setattr(self, key, logger)


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
    globals = {}
    w_globals = space.wrap(globals) 
    args_w = [space.wrap(ii) for ii in args]
    ec = space.getexecutioncontext()
    code = func.func_code
    code = PyCode()._from_code(code)
    frame = code.create_frame(space, w_globals)
    frame.setfastscope(args_w)
    return frame.run()
