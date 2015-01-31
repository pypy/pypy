"""

Higher-level constructs to use multiple cores on a pypy-stm.

Internally based on threads, this module should hide them completely and
give a simple-to-use API.

Note that some rough edges still need to be sorted out; for now you
have to explicitly set the number of threads to use by calling
set_num_threads(), or you get a default of 4.

"""

from __future__ import with_statement
import sys, thread, collections, cStringIO, linecache

try:
    from pypystm import atomic, is_atomic
except ImportError:
    # Not a STM-enabled PyPy.  We can use a regular lock for 'atomic',
    # which is good enough for our purposes.  With this limited version,
    # an atomic block in thread X will not prevent running thread Y, if
    # thread Y is not within an atomic block at all.
    atomic = thread.allocate_lock()
    def is_atomic():
        return atomic.locked()

try:
    from __pypy__.thread import signals_enabled
except ImportError:
    # Not a PyPy at all.
    class _SignalsEnabled(object):
        def __enter__(self):
            pass
        def __exit__(self, *args):
            pass
    signals_enabled = _SignalsEnabled()

try:
    from pypystm import hint_commit_soon
except ImportError:
    # Not a STM-enabled PyPy.
    def hint_commit_soon():
        return None

try:
    from pypystm import getsegmentlimit
except ImportError:
    # Not a STM-enabled PyPy.
    def getsegmentlimit():
        return 1


class TransactionError(Exception):
    pass


def add(f, *args, **kwds):
    """Register a new transaction that will be done by 'f(*args, **kwds)'.
    Must be called within the transaction in the "with TransactionQueue()"
    block, or within a transaction started by this one, directly or
    indirectly.
    """
    _thread_local.pending.append((f, args, kwds))


class TransactionQueue(object):
    """Use in 'with TransactionQueue():'.  Creates a queue of
    transactions.  The first transaction in the queue is the content of
    the 'with:' block, which is immediately started.

    Any transaction can register new transactions that will be run
    after the current one is finished, using the global function add().
    """

    def __init__(self, nb_segments=0):
        if nb_segments <= 0:
            nb_segments = getsegmentlimit()
        _thread_pool.ensure_threads(nb_segments)

    def __enter__(self):
        if hasattr(_thread_local, "pending"):
            raise TransactionError(
                "recursive invocation of TransactionQueue()")
        if is_atomic():
            raise TransactionError(
                "invocation of TransactionQueue() from an atomic context")
        _thread_local.pending = []
        atomic.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        atomic.__exit__(exc_type, exc_value, traceback)
        pending = _thread_local.pending
        del _thread_local.pending
        if exc_type is None and len(pending) > 0:
            _thread_pool.run(pending)


# ____________________________________________________________


class _ThreadPool(object):

    def __init__(self):
        self.lock_running = thread.allocate_lock()
        self.lock_done_running = thread.allocate_lock()
        self.lock_done_running.acquire()
        self.nb_threads = 0
        self.deque = collections.deque()
        self.locks = []
        self.lock_deque = thread.allocate_lock()
        self.exception = []

    def ensure_threads(self, n):
        if n > self.nb_threads:
            with self.lock_running:
                for i in range(self.nb_threads, n):
                    assert len(self.locks) == self.nb_threads
                    self.nb_threads += 1
                    thread.start_new_thread(self.thread_runner, ())
                    # The newly started thread should run immediately into
                    # the case 'if len(self.locks) == self.nb_threads:'
                    # and release this lock.  Wait until it does.
                    self.lock_done_running.acquire()

    def run(self, pending):
        # For now, can't run multiple threads with each an independent
        # TransactionQueue(): they are serialized.
        with self.lock_running:
            assert self.exception == []
            assert len(self.deque) == 0
            deque = self.deque
            with self.lock_deque:
                deque.extend(pending)
                try:
                    for i in range(len(pending)):
                        self.locks.pop().release()
                except IndexError:     # pop from empty list
                    pass
            #
            self.lock_done_running.acquire()
            #
            if self.exception:
                exc_type, exc_value, exc_traceback = self.exception
                del self.exception[:]
                raise exc_type, exc_value, exc_traceback

    def thread_runner(self):
        deque = self.deque
        lock = thread.allocate_lock()
        lock.acquire()
        pending = []
        _thread_local.pending = pending
        lock_deque = self.lock_deque
        exception = self.exception
        #
        while True:
            #
            # Look at the deque and try to fetch the next item on the left.
            # If empty, we add our lock to the 'locks' list.
            lock_deque.acquire()
            if deque:
                next_transaction = deque.popleft()
                lock_deque.release()
            else:
                self.locks.append(lock)
                if len(self.locks) == self.nb_threads:
                    self.lock_done_running.release()
                lock_deque.release()
                #
                # Now wait until our lock is released.
                lock.acquire()
                continue
            #
            # Now we have a next_transaction.  Run it.
            assert len(pending) == 0
            while True:
                f, args, kwds = next_transaction
                with atomic:
                    if len(exception) == 0:
                        try:
                            f(*args, **kwds)
                        except:
                            exception.extend(sys.exc_info())
                del next_transaction
                #
                # If no new 'pending' transactions have been added, exit
                # this loop and go back to fetch more from the deque.
                if len(pending) == 0:
                    break
                #
                # If we have some new 'pending' transactions, add them
                # to the right of the deque and pop the next one from
                # the left.  As we do this atomically with the
                # 'lock_deque', we are sure that the deque cannot be
                # empty before the popleft().  (We do that even when
                # 'len(pending) == 1' instead of simply assigning the
                # single item to 'next_transaction', because it looks
                # like a good idea to preserve some first-in-first-out
                # approximation.)
                with self.lock_deque:
                    deque.extend(pending)
                    next_transaction = deque.popleft()
                    try:
                        for i in range(1, len(pending)):
                            self.locks.pop().release()
                    except IndexError:     # pop from empty list
                        pass
                del pending[:]


_thread_pool = _ThreadPool()
_thread_local = thread._local()


def XXXreport_abort_info(info):
    header = info[0]
    f = cStringIO.StringIO()
    if len(info) > 1:
        print >> f, 'Detected conflict:'
        for tb in info[1:]:
            filename = tb[0]
            coname = tb[1]
            lineno = tb[2]
            lnotab = tb[3]
            bytecodenum = tb[-1]
            for i in range(0, len(lnotab), 2):
                bytecodenum -= ord(lnotab[i])
                if bytecodenum < 0:
                    break
                lineno += ord(lnotab[i+1])
            print >> f, '  File "%s", line %d, in %s' % (
                filename, lineno, coname)
            line = linecache.getline(filename,lineno)
            if line: print >> f, '    ' + line.strip()
    print >> f, 'Transaction aborted, %.6f seconds lost (th%d' % (
        header[0] * 1E-9, header[2]),
    print >> f, 'abrt%d %s%s%d/%d)' % (
        header[1], 'atom '*header[3], 'inev '*(header[4]>1),
        header[5], header[6])
    sys.stderr.write(f.getvalue())


class threadlocalproperty(object):
    def __init__(self, *default):
        self.tl_default = default
        self.tl_name = intern(str(id(self)))

    def tl_get(self, obj):
        try:
            return obj._threadlocalproperties
        except AttributeError:
            return obj.__dict__.setdefault('_threadlocalproperties',
                                           thread._local())

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        return getattr(self.tl_get(obj), self.tl_name, *self.tl_default)

    def __set__(self, obj, value):
        setattr(self.tl_get(obj), self.tl_name, value)

    def __delete__(self, obj):
        delattr(self.tl_get(obj), self.tl_name)
