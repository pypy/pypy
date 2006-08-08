from pypy.rpython.objectmodel import we_are_translated
from pypy.interpreter import baseobjspace, gateway, argument, typedef
from pypy.interpreter.error import OperationError

from pypy.objspace.std.intobject import W_IntObject

from pypy.objspace.cclp.misc import ClonableCoroutine, w
from pypy.objspace.cclp.thunk import CSpaceThunk
from pypy.objspace.cclp.global_state import scheduler
from pypy.objspace.cclp.variable import newvar


def newspace(space, w_callable, __args__):
    args = __args__.normalize()
    # coro init
    w_coro = ClonableCoroutine(space)
    thunk = CSpaceThunk(space, w_callable, args, w_coro)
    w_coro.bind(thunk)
    if not we_are_translated():
        w("NEWSPACE, thread", str(id(w_coro)), "for", str(w_callable.name))
    w_space = W_CSpace(space, w_coro, parent=w_coro._cspace)
    w_coro._cspace = w_space

    scheduler[0].add_new_thread(w_coro)
    scheduler[0].schedule()

    return w_space
app_newspace = gateway.interp2app(newspace, unwrap_spec=[baseobjspace.ObjSpace,
                                                         baseobjspace.W_Root,
                                                         argument.Arguments])


def choose(space, w_n):
    assert isinstance(w_n, W_IntObject)
    n = space.int_w(w_n)
    cspace = ClonableCoroutine.w_getcurrent(space)._cspace
    if cspace != None:
        assert isinstance(cspace, W_CSpace)
        return cspace.choose(n)
    raise OperationError(space.w_RuntimeError,
                         space.wrap("choose is forbidden from the top-level space"))
app_choose = gateway.interp2app(choose)



class W_CSpace(baseobjspace.Wrappable):

    def __init__(self, space, thread, parent=None):
        assert isinstance(thread, ClonableCoroutine)
        assert (parent is None) or isinstance(parent, W_CSpace)
        self.space = space # the object space ;-)
        self.parent = parent
        self.main_thread = thread
        # choice mgmt
        self._choice = newvar(space)
        self._committed = newvar(space)
        # constraint store ...
        

    def w_ask(self):
        scheduler[0].wait_stable(self)
        self.space.wait(self._choice)
        return self._choice

    def choose(self, n):
        assert n > 1
        scheduler[0].wait_stable(self)
        assert self.space.is_true(self.space.is_free(self._choice))
        assert self.space.is_true(self.space.is_free(self._committed))
        self.space.bind(self._choice, self.space.wrap(n))
        self.space.wait(self._committed)
        committed = self._committed
        self._committed = newvar(self.space)
        return committed

    def w_commit(self, w_n):
        assert self.space.is_true(self.space.is_bound(self._choice))
        assert 0 < self.space.int_w(w_n)
        assert self.space.int_w(w_n) <= self._choice.w_bound_to
        self.space.bind(self._committed, w_n)
        self._choice = newvar(self.space)


    def tell(self, w_constraint):
        pass

W_CSpace.typedef = typedef.TypeDef("W_CSpace",
    ask = gateway.interp2app(W_CSpace.w_ask),
    commit = gateway.interp2app(W_CSpace.w_commit))





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

