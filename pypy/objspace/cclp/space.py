from pypy.rpython.objectmodel import we_are_translated
from pypy.interpreter import baseobjspace, gateway, argument, typedef
from pypy.interpreter.error import OperationError

from pypy.objspace.cclp.misc import ClonableCoroutine, w
from pypy.objspace.cclp.thunk import FutureThunk, ProcedureThunk
from pypy.objspace.cclp.global_state import scheduler

def newspace(space, w_callable, __args__):
    try:
        args = __args__.normalize()
        # coro init
        w_coro = ClonableCoroutine(space)
        thunk = ProcedureThunk(space, w_callable, args, w_coro)
        w_coro.bind(thunk)
        if not we_are_translated():
            w("NEWSPACE, thread", str(id(w_coro)), "for", str(w_callable.name))

            w_space = W_CSpace(space, w_coro, parent=w_coro._cspace)
            w_coro._cspace = w_space

            scheduler[0].add_new_thread(w_coro)
            scheduler[0].schedule()
    except:
        print "oh, uh"

    return w_space
app_newspace = gateway.interp2app(newspace, unwrap_spec=[baseobjspace.ObjSpace,
                                                         baseobjspace.W_Root,
                                                         argument.Arguments])

class W_CSpace(baseobjspace.Wrappable):

    def __init__(self, space, thread, parent=None):
        assert isinstance(thread, ClonableCoroutine)
        assert (parent is None) or isinstance(parent, CSpace)
        self.space = space # the object space ;-)
        self.parent = parent
        self.main_thread = thread

    def w_ask(self):
        scheduler[0].wait_stable(self)
        return self.space.newint(0)

W_CSpace.typedef = typedef.TypeDef("W_CSpace",
    ask = gateway.interp2app(W_CSpace.w_ask))




##     def is_top_level(self):
##         return self.parent is None

##     def current_space():
##         #XXX return w_getcurrent().cspace
##         pass


##     def clone(self):
##         if self.is_top_level():
##             raise OperationError(self.space.w_RuntimeError,
##                                  self.space.wrap("Clone"+forbidden_boilerplate))
##         new = CSpace(self.distributor.clone(), parent=self)
##         new.distributor.cspace = new
##         for thread in self.threads:
##             tclone = thread.clone()
##             tclone.cspace = new
##             new.threads[tclone] = True

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
