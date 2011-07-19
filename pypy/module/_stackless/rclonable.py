from pypy.module._stackless.interp_coroutine import AbstractThunk, Coroutine
from pypy.rlib.rgc import gc_swap_pool, gc_clone
from pypy.rlib.objectmodel import we_are_translated


class InterpClonableMixin:
    local_pool = None
    _mixin_ = True

    def hello_local_pool(self):
        if we_are_translated():
            self.saved_pool = gc_swap_pool(self.local_pool)

    def goodbye_local_pool(self):
        if we_are_translated():
            self.local_pool = gc_swap_pool(self.saved_pool)
            self.saved_pool = None

    def clone_into(self, copy, extradata=None):
        if not we_are_translated():
            raise NotImplementedError
        # cannot gc_clone() directly self, because it is not in its own
        # local_pool.  Moreover, it has a __del__, which cloning doesn't
        # support properly at the moment.
        copy.parent = self.parent
        # the hello/goodbye pair has two purposes: it forces
        # self.local_pool to be computed even if it was None up to now,
        # and it puts the 'data' tuple in the correct pool to be cloned.
        self.hello_local_pool()
        data = (self.frame, extradata)
        self.goodbye_local_pool()
        # clone!
        data, copy.local_pool = gc_clone(data, self.local_pool)
        copy.frame, extradata = data
        copy.thunk = self.thunk # in case we haven't switched to self yet
        return extradata


class InterpClonableCoroutine(Coroutine, InterpClonableMixin):

    def hello(self):
        self.hello_local_pool()

    def goodbye(self):
        self.goodbye_local_pool()

    def clone(self):
        # hack, this is overridden in AppClonableCoroutine
        if self.getcurrent() is self:
            raise RuntimeError("clone() cannot clone the current coroutine; "
                               "use fork() instead")
        copy = InterpClonableCoroutine(self.costate)
        self.clone_into(copy)
        return copy


class ForkThunk(AbstractThunk):
    def __init__(self, coroutine):
        self.coroutine = coroutine
        self.newcoroutine = None
    def call(self):
        oldcoro = self.coroutine
        self.coroutine = None
        newcoro = oldcoro.clone()
        newcoro.parent = oldcoro
        self.newcoroutine = newcoro

def fork():
    """Fork, as in the Unix fork(): the call returns twice, and the return
    value of the call is either the new 'child' coroutine object (if returning
    into the parent), or None (if returning into the child).  This returns
    into the parent first, which can switch to the child later.
    """
    current = InterpClonableCoroutine.getcurrent()
    if not isinstance(current, InterpClonableCoroutine):
        raise RuntimeError("fork() in a non-clonable coroutine")
    thunk = ForkThunk(current)
    coro_fork = InterpClonableCoroutine()
    coro_fork.bind(thunk)
    coro_fork.switch()
    # we resume here twice.  The following would need explanations about
    # why it returns the correct thing in both the parent and the child...
    return thunk.newcoroutine

##    from pypy.rpython.lltypesystem import lltype, lloperation
##    lloperation.llop.debug_view(lltype.Void, current, thunk,
##        lloperation.llop.gc_x_size_header(lltype.Signed))
