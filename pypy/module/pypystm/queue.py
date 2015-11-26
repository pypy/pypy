"""
The class pypystm.queue, an unordered minimal queue
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, oefmt
from pypy.module.thread.error import wrap_thread_error

from rpython.rlib import rstm, rerased

erase, unerase = rerased.new_erasing_pair("stmdictitem")


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
        self.q.put(erase(w_item))

    @unwrap_spec(block=int)
    def get_w(self, space, block=1, w_timeout=None):
        """Remove and return an item from the queue.
        The 'block' and 'timeout' arguments are like Queue.Queue.get().
        Note that using them is inefficient so far.
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
        return unerase(gcref)

    def task_done_w(self, space):
        """Indicate that a formerly enqueued task is complete.
        See Queue.Queue.task_done().

        Note that we cannot easily detect if task_done() is called more
        times than there were items placed in the queue.  This situation
        is detect by join() instead.
        """
        self.q.task_done()

    def join_w(self, space):
        """Blocks until all items in the Queue have been gotten and processed.
        See Queue.Queue.join().

        Raises ValueError if we detect that task_done() has been called
        more times than there were items placed in the queue.
        """
        res = self.q.join()
        if res != 0:
            raise oefmt(space.w_ValueError,
                'task_done() called too many times '
                '(%d more than there were items placed in the queue)', -res)


def W_Queue___new__(space, w_subtype):
    r = space.allocate_instance(W_Queue, w_subtype)
    r.__init__()
    return space.wrap(r)

W_Queue.typedef = TypeDef(
    'pypystm.queue',
    __new__ = interp2app(W_Queue___new__),
    get = interp2app(W_Queue.get_w),
    put = interp2app(W_Queue.put_w),
    task_done = interp2app(W_Queue.task_done_w),
    join = interp2app(W_Queue.join_w),
)
