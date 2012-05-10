"""

Higher-level constructs to use multiple cores on a pypy-stm.

Internally based on threads, this module should hide them completely and
give a simple-to-use API.

"""

from __future__ import with_statement
import sys, thread, collections

try:
    from thread import atomic
except ImportError:
    # Not a STM-enabled PyPy.  We can still provide a version of 'atomic'
    # that is good enough for our purposes.  With this limited version,
    # an atomic block in thread X will not prevent running thread Y, if
    # thread Y is not within an atomic block at all.
    _atomic_global_lock = thread.allocate_lock()
    class _Atomic(object):
        def __enter__(self):
            _atomic_global_lock.acquire()
        def __exit__(self, *args):
            _atomic_global_lock.release()
    atomic = _Atomic()


def set_num_threads(self, num):
    """Set the number of threads to use."""
    if num < 1:
        raise ValueError("'num' must be at least 1, got %r" % (num,))
    if _thread_pool.in_transaction:
        raise TransactionError("cannot change the number of threads "
                               "while running transactions")
    _thread_pool.num_threads = num


class TransactionError(Exception):
    pass


# XXX right now uses the same API as the old pypy-stm.  This will
# be redesigned later.

def add(f, *args, **kwds):
    """Register the call 'f(*args, **kwds)' as running a new
    transaction.  If we are currently running in a transaction too, the
    new transaction will only start after the end of the current
    transaction.  Note that if the current transaction or another running
    in the meantime raises an exception, all pending transactions are
    cancelled.
    """
    _thread_local.pending.append((f, args, kwds))


def run():
    """Run the pending transactions, as well as all transactions started
    by them, and so on.  The order is random and undeterministic.  Must
    be called from the main program, i.e. not from within another
    transaction.  If at some point all transactions are done, returns.
    If a transaction raises an exception, it propagates here; in this
    case all pending transactions are cancelled.
    """
    tpool = _thread_pool
    if tpool.in_transaction:
        raise TransactionError("recursive invocation of transaction.run()")
    if not _thread_local.pending:
        return     # nothing to do
    try:
        tpool.setup()
        tpool.run()
    finally:
        tpool.teardown()
    tpool.reraise()

# ____________________________________________________________


class _ThreadPool(object):

    def __init__(self):
        self.num_threads = 4    # XXX default value, tweak
        self.in_transaction = False

    def setup(self):
        # a mutex to protect parts of _grab_next_thing_to_do()
        self.lock_mutex = thread.allocate_lock()
        # this lock is released if and only if there are things to do in
        # 'self.pending'; both are modified together, with the lock_mutex.
        self.lock_pending = thread.allocate_lock()
        # this lock is released when we are finished at the end
        self.lock_if_released_then_finished = thread.allocate_lock()
        self.lock_if_released_then_finished.acquire()
        #
        self.pending = _thread_local.pending
        # there must be pending items at the beginning, which means that
        # 'lock_pending' can indeed be released
        assert self.pending
        _thread_local.pending = None
        #
        self.num_waiting_threads = 0
        self.finished = False
        self.got_exception = []
        self.in_transaction = True

    def run(self):
        # start the N threads
        for i in range(self.num_threads):
            thread.start_new_thread(self._run_thread, ())
        # now wait.  When we manage to acquire the following lock, then
        # we are finished.
        self.lock_if_released_then_finished.acquire()

    def teardown(self):
        self.in_transaction = False
        self.pending = None
        self.lock_if_released_then_finished = None
        self.lock_pending = None
        self.lock_mutex = None
        _thread_local.pending = collections.deque()

    def reraise(self):
        exc = self.got_exception
        self.got_exception = None
        if exc:
            raise exc[0], exc[1], exc[2]    # exception, value, traceback

    def _run_thread(self):
        tloc_pending = _thread_local.pending
        got_exception = self.got_exception
        try:
            while True:
                self._do_it(self._grab_next_thing_to_do(tloc_pending),
                            got_exception)
        except _Done:
            pass

    def _grab_next_thing_to_do(self, tloc_pending):
        if tloc_pending:
            # grab the next thing to do from the thread-local deque
            next = tloc_pending.popleft()
            # add the rest, if any, to the global 'pending'
            if tloc_pending:
                #
                self.lock_mutex.acquire()
                if not self.pending:
                    # self.pending is empty so far, but we are adding stuff.
                    # we have to release the following lock.
                    self.lock_pending.release()
                self.pending.extend(tloc_pending)
                self.lock_mutex.release()
                #
                tloc_pending.clear()
            return next
        #
        self.lock_mutex.acquire()
        while True:
            try:
                next = self.pending.popleft()
            except IndexError:
                # self.pending is empty: wait until it no longer is.
                pass
            else:
                # self.pending was not empty.  If now it is empty, then
                # fix the status of 'lock_pending'.
                if not self.pending:
                    self.lock_pending.acquire()
                self.lock_mutex.release()
                return next
            #
            # first check if all N threads are waiting here.
            self.num_waiting_threads += 1
            if self.num_waiting_threads == self.num_threads:
                # yes, so finished!  unlock this to wake up the other
                # threads, which are all waiting on the following acquire().
                self.finished = True
                self.lock_pending.release()
            #
            self.lock_mutex.release()
            self.lock_pending.acquire()
            self.lock_pending.release()
            self.lock_mutex.acquire()
            #
            self.num_waiting_threads -= 1
            if self.finished:
                if self.num_waiting_threads == 0:    # last one to leave?
                    self.lock_if_released_then_finished.release()
                self.lock_mutex.release()
                raise _Done

    @staticmethod
    def _do_it((f, args, kwds), got_exception):
        # this is a staticmethod in order to make sure that we don't
        # accidentally use 'self' in the atomic block.
        with atomic:
            if got_exception:
                return    # return early if already an exception to reraise
            try:
                f(*args, **kwds)
            except:
                got_exception[:] = sys.exc_info()

_thread_pool = _ThreadPool()


class _Done(Exception):
    pass


class _ThreadLocal(thread._local):
    def __init__(self):
        self.pending = collections.deque()

_thread_local = _ThreadLocal()
