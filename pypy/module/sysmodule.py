from pypy.interpreter.baseobjspace import OperationError
from pypy.interpreter.extmodule import *
import sys

class Sys(BuiltinModule):
    __pythonname__ = 'sys'

    def __init__(self, space):
        BuiltinModule.__init__(self, space)

        import sys, os
        import pypy

        opd = os.path.dirname
        
        pypydir = opd(opd(os.path.abspath(pypy.__file__)))
        
        appdir = os.path.join(pypydir, 'pypy', 'appspace')

        self.path = appdata([appdir] + [p for p in sys.path if p != pypydir])
    
    stdout = appdata(sys.stdout)

    def displayhook(self, w_x):
        space = self.space
        w = space.wrap
        if w_x != space.w_None:
            try:
                print space.unwrap(self.space.repr(w_x))
            except OperationError:
                print "! could not print", w_x
            space.setitem(space.w_builtins, w('_'), w_x)
    displayhook = appmethod(displayhook)
    
