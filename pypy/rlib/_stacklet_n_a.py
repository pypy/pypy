from pypy.rlib import rstacklet

class StackletGcRootFinder:
    new     = staticmethod(rstacklet._new)
    switch  = staticmethod(rstacklet._switch)
    destroy = staticmethod(rstacklet._destroy)
