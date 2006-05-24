from pypy.module.stackless.interp_coroutine import Coroutine, AbstractThunk
from pypy.rpython.rgc import gc_swap_pool, gc_clone


class ClonableCoroutine(Coroutine):
    local_pool = None

    def hello(self):
        self.saved_pool = gc_swap_pool(self.local_pool)

    def goodbye(self):
        self.local_pool = gc_swap_pool(self.saved_pool)

    def clone(self):
        if self.getcurrent() is self:
            raise RuntimeError("clone() cannot clone the current coroutine; "
                               "use fork() instead")
        if self.local_pool is None:   # force it now
            self.local_pool = gc_swap_pool(gc_swap_pool(None))
        # cannot gc_clone() directly self, because it is not in its own
        # local_pool.  Moreover, it has a __del__, which cloning doesn't
        # support properly at the moment.
        copy = ClonableCoroutine(self.costate)
        copy.parent = self.parent
        copy.frame, copy.local_pool = gc_clone(self.frame, self.local_pool)
        return copy


class ForkThunk(AbstractThunk):
    def __init__(self, coroutine):
        self.coroutine = coroutine
        self.newcoroutine = None
    def call(self):
        oldcoro = self.coroutine
        self.coroutine = None
        self.newcoroutine = oldcoro.clone()

def fork():
    """Fork, as in the Unix fork(): the call returns twice, and the return
    value of the call is either the new 'child' coroutine object (if returning
    into the parent), or None (if returning into the child).  This returns
    into the parent first, which can switch to the child later.
    """
    current = ClonableCoroutine.getcurrent()
    if not isinstance(current, ClonableCoroutine):
        raise RuntimeError("fork() in a non-clonable coroutine")
    thunk = ForkThunk(current)
    coro_fork = ClonableCoroutine()
    coro_fork.bind(thunk)
    coro_fork.switch()
    # we resume here twice.  The following would need explanations about
    # why it returns the correct thing in both the parent and the child...
    return thunk.newcoroutine
