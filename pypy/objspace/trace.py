# ______________________________________________________________________
import autopath
import sys, operator, types
import pypy
from pypy.objspace.std import StdObjSpace
from pypy.interpreter.baseobjspace import ObjSpace

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


Space = TraceObjSpace

# ______________________________________________________________________
# End of trace.py
