"""
The class pypystm.queue, an unordered minimal queue
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, oefmt
from pypy.module.thread.error import wrap_thread_error

from rpython.rlib import rstm
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.rtyper.annlowlevel import cast_instance_to_gcref


class Cache:
    def __init__(self, space):
        self.w_Empty = space.new_exception_class("pypystm.Empty")


class W_Queue(W_Root):

    def __init__(self):
        self.q = rstm.create_queue()

    def put_w(self, space, w_item):
        """Put an item into the queue.
        This queue does not support a maximum size.
        """
        self.q.put(cast_instance_to_gcref(w_item))

    @unwrap_spec(block=int)
    def get_w(self, space, block=1, w_timeout=None):
        """Remove and return an item from the queue.

        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until an item is available. If 'timeout' is
        a non-negative number, it blocks at most 'timeout' seconds and raises
        the Empty exception if no item was available within that time.
        Otherwise ('block' is false), return an item if one is immediately
        available, else raise the Empty exception ('timeout' is ignored
        in that case).
        """
        if block == 0:
            timeout = 0.0     # 'w_timeout' ignored in this case
        elif space.is_none(w_timeout):
            timeout = -1.0     # no timeout
        else:
            timeout = space.float_w(w_timeout)
            if timeout < 0.0:
                raise oefmt(space.w_ValueError,
                            "'timeout' must be a non-negative number")

        if space.config.translation.stm:    # for tests
            if rstm.is_atomic() and timeout != 0.0:
                raise wrap_thread_error(space,
                    "can't use queue.get(block=True) in an atomic context")

        gcref = self.q.get(timeout)
        if not gcref:
            raise OperationError(space.fromcache(Cache).w_Empty,
                                 space.w_None)
        return cast_gcref_to_instance(W_Root, gcref)


def W_Queue___new__(space, w_subtype):
    r = space.allocate_instance(W_Queue, w_subtype)
    r.__init__()
    return space.wrap(r)

W_Queue.typedef = TypeDef(
    'pypystm.queue',
    __new__ = interp2app(W_Queue___new__),
    get = interp2app(W_Queue.get_w),
    put = interp2app(W_Queue.put_w),
)
