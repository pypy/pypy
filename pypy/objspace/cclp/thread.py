from pypy.interpreter import gateway, baseobjspace, argument
from pypy.rpython.objectmodel import we_are_translated

from pypy.objspace.cclp.types import W_Var, W_Future, W_FailedValue
from pypy.objspace.cclp.misc import w, v, ClonableCoroutine
from pypy.objspace.cclp.thunk import FutureThunk, ProcedureThunk
from pypy.objspace.cclp.global_state import scheduler


#-- Future --------------------------------------------------

def future(space, w_callable, __args__):
    """returns a future result"""
    #XXX we could be much more lazy wrt coro creation
    args = __args__.normalize()
    # coro init
    coro = ClonableCoroutine(space)
    # computation space is the same as in the parent
    #coro.cspace = ClonableCoroutine.w_getcurrent(space).cspace
    # feed the coro
    w_Future = W_Future(space)
    thunk = FutureThunk(space, w_callable, args, w_Future, coro)
    coro.bind(thunk)
    if not we_are_translated():
        w("FUTURE", str(id(coro)), "for", str(w_callable.name))
    scheduler[0].add_new_thread(coro)
    return w_Future
app_future = gateway.interp2app(future, unwrap_spec=[baseobjspace.ObjSpace,
                                                     baseobjspace.W_Root,
                                                     argument.Arguments])

#-- plain Coroutine -----------------------------------------

def stacklet(space, w_callable, __args__):
    """returns a coroutine object"""
    args = __args__.normalize()
    # coro init
    coro = ClonableCoroutine(space)
    # computation space is the same as in the parent
    #coro.cspace = ClonableCoroutine.w_getcurrent(space).cspace
    thunk = ProcedureThunk(space, w_callable, args, coro)
    coro.bind(thunk)
    print we_are_translated()
    if not we_are_translated():
        w("STACKLET", str(id(coro)), "for", str(w_callable.name))
    scheduler[0].add_new_thread(coro)
    scheduler[0].schedule()
    return coro
app_stacklet = gateway.interp2app(stacklet, unwrap_spec=[baseobjspace.ObjSpace,
                                                         baseobjspace.W_Root,
                                                         argument.Arguments])


def this_thread(space):
    return ClonableCoroutine.w_getcurrent(space)
app_this_thread = gateway.interp2app(this_thread)
