from pypy.interpreter.error import OperationError
from pypy.objspace.cclp.misc import ClonableCoroutine

class CSpace:

    def __init__(self, space, distributor, parent=None):
        assert isinstance(distributor, ClonableCoroutine)
        assert (parent is None) or isinstance(parent, CSpace)
        self.space = space # the object space ;-)
        self.parent = parent
        self.distributor = distributor
        self.threads = {} # the eventual other threads

    def is_top_level(self):
        return self.parent is None

##     def current_space():
##         #XXX return w_getcurrent().cspace
##         pass

##     def newspace():
##         #XXX fork ?
##         pass

    def clone(self):
        if self.is_top_level():
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("Clone"+forbidden_boilerplate))
        new = CSpace(self.distributor.clone(), parent=self)
        new.distributor.cspace = new
        for thread in self.threads:
            tclone = thread.clone()
            tclone.cspace = new
            new.threads[tclone] = True

##     def choose(self, n):
##         if self.is_top_level():
##             raise OperationError(self.space.w_RuntimeError,
##                                  self.space.wrap("Choose"+forbidden_boilerplate))

##     def ask(self):
##         if self.is_top_level():
##             raise OperationError(self.space.w_RuntimeError,
##                                  self.space.wrap("Ask"+forbidden_boilerplate))
##         #XXX basically hang until a call to choose, then return n

##     def commit(self, n):
##         if self.is_top_level():
##             raise OperationError(self.space.w_RuntimeError,
##                                  self.space.wrap("Commit"+forbidden_boilerplate))
##         # ensure 0 < n < chosen n
##         # ...
