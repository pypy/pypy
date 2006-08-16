from pypy.rpython.objectmodel import we_are_translated
from pypy.interpreter import baseobjspace, gateway, argument, typedef
from pypy.interpreter.error import OperationError

from pypy.objspace.std.intobject import W_IntObject

from pypy.objspace.cclp.misc import ClonableCoroutine, w
from pypy.objspace.cclp.thunk import CSpaceThunk, PropagatorThunk
from pypy.objspace.cclp.global_state import scheduler
from pypy.objspace.cclp.variable import newvar
from pypy.objspace.cclp.types import ConsistencyError, Solution, W_Var
from pypy.objspace.cclp.interp_var import interp_bind, interp_free

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
        try:
            return space.newint(cspace.choose(w_n.intval))
        except ConsistencyError:
            raise OperationError(space.w_ConsistencyError,
                                 space.wrap("the space is failed"))
    raise OperationError(space.w_RuntimeError,
                         space.wrap("choose is forbidden from the top-level space"))
app_choose = gateway.interp2app(choose)


from pypy.objspace.cclp.constraint import constraint

def tell(space, w_constraint):
    assert isinstance(w_constraint, constraint.W_AbstractConstraint)
    ClonableCoroutine.w_getcurrent(space)._cspace.tell(w_constraint)
app_tell = gateway.interp2app(tell)


class W_CSpace(baseobjspace.Wrappable):

    def __init__(self, space, thread, parent):
        assert isinstance(thread, ClonableCoroutine)
        assert (parent is None) or isinstance(parent, W_CSpace)
        self.space = space # the object space ;-)
        self.parent = parent
        self.distributor = thread
        # choice mgmt
        self._choice = newvar(space)
        self._committed = newvar(space)
        # status, merging
        self._solution = newvar(space)
        self._finished = newvar(space)
        self._failed = False
        # constraint store ...
        self._store = {} # name -> var
        
    def register_var(self, cvar):
        self._store[cvar.name] = cvar

    def w_ask(self):
        scheduler[0].wait_stable(self)
        self.space.wait(self._choice)
        choice = self._choice.w_bound_to
        self._choice = newvar(self.space)
        self._last_choice = choice.intval
        return choice

    def choose(self, n):
        assert n > 1
        scheduler[0].wait_stable(self)
        if self._failed: #XXX set by any propagator
            raise ConsistencyError
        assert interp_free(self._choice)
        assert interp_free(self._committed)
        interp_bind(self._choice, self.space.wrap(n))
        self.space.wait(self._committed)
        committed = self._committed.w_bound_to
        self._committed = newvar(self.space)
        return committed

    def w_commit(self, w_n):
        assert isinstance(w_n, W_IntObject)
        n = w_n.intval
        assert interp_free(self._committed)
        assert n > 0
        assert n <= self._last_choice
        interp_bind(self._committed, n)

    def tell(self, w_constraint):
        space = self.space
        w_coro = ClonableCoroutine(space)
        w_coro._cspace = self
        thunk = PropagatorThunk(space, w_constraint, w_coro)
        w_coro.bind(thunk)
        if not we_are_translated():
            w("PROPAGATOR in thread", str(id(w_coro)))
        scheduler[0].add_new_thread(w_coro)
        scheduler[0].schedule()

    def fail(self):
        self._failed = True
        interp_bind(self._finished, True)
        interp_bind(self._choice, self.space.newint(0))
        self._store = {}

    def w_merge(self):
        self._store = {}
        return self._solution



W_CSpace.typedef = typedef.TypeDef("W_CSpace",
    ask = gateway.interp2app(W_CSpace.w_ask),
    commit = gateway.interp2app(W_CSpace.w_commit),
    merge = gateway.interp2app(W_CSpace.w_merge))
