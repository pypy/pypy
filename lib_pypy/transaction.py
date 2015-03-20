"""

Higher-level constructs to use multiple cores on a pypy-stm.

Internally based on threads, this module should hide them completely and
give a simple-to-use API.

Note that some rough edges still need to be sorted out; for now you
have to explicitly set the number of threads to use by passing the
'nb_segments' argument to TransactionQueue(), or you get a default of 4
(or whatever the compiled-in maximum is).
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
    from pypystm import hint_commit_soon, getsegmentlimit
    from pypystm import hashtable, stmset, stmdict
    from pypystm import local, time, clock
except ImportError:
    # Not a STM-enabled PyPy.
    def hint_commit_soon():
        return None
    def getsegmentlimit():
        return 1
    hashtable = dict
    stmset = set
    stmdict = dict
    from time import time, clock

class stmidset(object):
    def __init__(self):
        self._hashtable = hashtable()

    def add(self, key):
        self._hashtable[id(key)] = key

    def __contains__(self, key):
        return id(key) in self._hashtable

    def remove(self, key):
        del self._hashtable[id(key)]

    def discard(self, key):
        try:
            del self._hashtable[id(key)]
        except KeyError:
            pass

class stmiddict(object):
    def __init__(self):
        self._hashtable = hashtable()

    def __getitem__(self, key):
        return self._hashtable[id(key)][1]

    def __setitem__(self, key, value):
        self._hashtable[id(key)] = (key, value)

    def __delitem__(self, key):
        del self._hashtable[id(key)]

    def __contains__(self, key):
        return id(key) in self._hashtable

    def get(self, key, default=None):
        try:
            return self._hashtable[id(key)][1]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        return self._hashtable.setdefault(id(key), (key, default))[1]


# ------------------------------------------------------------


class TransactionError(Exception):
    pass


class TransactionQueue(object):
    """A queue of pending transactions.

    Use the add() method to register new transactions into the queue.
    Afterwards, call run() once.  While transactions run, it is possible
    to add() more transactions, which will run after the current one is
    finished.  The run() call only returns when the queue is completely
    empty.
    """

    def __init__(self):
        self._deque = collections.deque()
        self._pending = self._deque
        self._number_transactions_exec = 0

    def add(self, f, *args, **kwds):
        """Register a new transaction to be done by 'f(*args, **kwds)'.
        """
        # note: 'self._pending.append' can be two things here:
        # * if we are outside run(), it is the regular deque.append method;
        # * if we are inside run(), self._pending is a thread._local()
        #   and then its append attribute is the append method of a
        #   thread-local list.
        self._pending.append((f, args, kwds))

    def run(self, nb_segments=0):
        """Run all transactions, and all transactions started by these
        ones, recursively, until the queue is empty.  If one transaction
        raises, run() re-raises the exception and the unexecuted transaction
        are left in the queue.
        """
        if is_atomic():
            raise TransactionError(
                "TransactionQueue.run() cannot be called in an atomic context")
        if not self._pending:
            return
        if nb_segments <= 0:
            nb_segments = getsegmentlimit()

        assert self._pending is self._deque, "broken state"
        try:
            self._pending = thread._local()
            lock_done_running = thread.allocate_lock()
            lock_done_running.acquire()
            lock_deque = thread.allocate_lock()
            locks = []
            exception = []
            args = (locks, lock_done_running, lock_deque,
                    exception, nb_segments)
            #
            for i in range(nb_segments):
                thread.start_new_thread(self._thread_runner, args)
            #
            # The threads run here, and they will release this lock when
            # they are all finished.
            lock_done_running.acquire()
            #
            assert len(locks) == nb_segments
            for lock in locks:
                lock.release()
            #
        finally:
            self._pending = self._deque
        #
        if exception:
            exc_type, exc_value, exc_traceback = exception
            raise exc_type, exc_value, exc_traceback

    def number_of_transactions_executed(self):
        if self._pending is self._deque:
            return self._number_transactions_exec
        raise TransactionError("TransactionQueue.run() is currently running")

    def _thread_runner(self, locks, lock_done_running, lock_deque,
                       exception, nb_segments):
        pending = []
        self._pending.append = pending.append
        deque = self._deque
        lock = thread.allocate_lock()
        lock.acquire()
        next_transaction = None
        count = [0]
        #
        def _pause_thread():
            self._number_transactions_exec += count[0]
            count[0] = 0
            locks.append(lock)
            if len(locks) == nb_segments:
                lock_done_running.release()
            lock_deque.release()
            #
            # Now wait until our lock is released.
            lock.acquire()
            return len(locks) == nb_segments
        #
        while not exception:
            assert next_transaction is None
            #
            # Look at the deque and try to fetch the next item on the left.
            # If empty, we add our lock to the 'locks' list.
            lock_deque.acquire()
            if deque:
                next_transaction = deque.popleft()
                lock_deque.release()
            else:
                if _pause_thread():
                    return
                continue
            #
            # Now we have a next_transaction.  Run it.
            assert len(pending) == 0
            while True:
                f, args, kwds = next_transaction
                # The next hint_commit_soon() is essential: without it, the
                # current transaction is short, so far, but includes everything
                # after some lock.acquire() done recently.  That means that
                # anything we do in the atomic section will run with the lock
                # still acquired.  This prevents any parallelization.
                hint_commit_soon()
                with atomic:
                    if exception:
                        break
                    next_transaction = None
                    try:
                        with signals_enabled:
                            count[0] += 1
                            f(*args, **kwds)
                    except:
                        exception.extend(sys.exc_info())
                        break
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
                with lock_deque:
                    deque.extend(pending)
                    next_transaction = deque.popleft()
                    try:
                        for i in range(1, len(pending)):
                            locks.pop().release()
                    except IndexError:     # pop from empty list
                        pass
                del pending[:]
        #
        # We exit here with an exception.  Re-add 'next_transaction'
        # if it is not None.
        lock_deque.acquire()
        if next_transaction is not None:
            deque.appendleft(next_transaction)
            next_transaction = None
        while not _pause_thread():
            lock_deque.acquire()


# ____________________________________________________________


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
    def __init__(self, default_factory=None):
        self.tl_default_factory = default_factory
        self.tl_name = intern('tlprop.%d' % id(self))

    def tl_get(self, obj):
        try:
            return obj._threadlocalproperties
        except AttributeError:
            return obj.__dict__.setdefault('_threadlocalproperties',
                                           thread._local())

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        try:
            return getattr(self.tl_get(obj), self.tl_name)
        except AttributeError:
            if self.tl_default_factory is None:
                raise
            result = self.tl_default_factory()
            setattr(self.tl_get(obj), self.tl_name, result)
            return result

    def __set__(self, obj, value):
        setattr(self.tl_get(obj), self.tl_name, value)

    def __delete__(self, obj):
        delattr(self.tl_get(obj), self.tl_name)
