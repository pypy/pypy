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

try:
    from _weakref import weakkeyiddict
except ImportError:
    # Not a STM-enabled PyPy.
    from _weakkeyiddict import weakkeyiddict

try:
    from pypystm import queue, Empty
except ImportError:
    from Queue import Queue as queue
    from Queue import Empty

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
    _nb_threads = 0
    _thread_queue = queue()

    def __init__(self):
        self._queue = queue()

    def add(self, f, *args, **kwds):
        """Register a new transaction to be done by 'f(*args, **kwds)'.
        """
        self._queue.put((f, args, kwds))

    def add_generator(self, generator_iterator):
        """Register N new transactions to be done by a generator-iterator
        object.  Each 'yield' marks the limit of transactions.
        """
        def transact_until_yield():
            # Ask for the next item in this transaction.  If we get it,
            # then the 'for' loop below adds this function again and
            # returns.
            for ignored_yielded_value in generator_iterator:
                self.add(transact_until_yield)
                return
        self.add(transact_until_yield)

    def run(self, nb_segments=0):
        """Run all transactions, and all transactions started by these
        ones, recursively, until the queue is empty.  If one transaction
        raises, run() re-raises the exception.
        """
        if is_atomic():
            raise TransactionError(
                "TransactionQueue.run() cannot be called in an atomic context")
        if nb_segments <= 0:
            nb_segments = getsegmentlimit()
        while TransactionQueue._nb_threads < nb_segments:
            with atomic:
                if TransactionQueue._nb_threads >= nb_segments:
                    break
                TransactionQueue._nb_threads += 1
            thread.start_new_thread(TransactionQueue._thread_runner, ())
        #
        self._exception = []
        for i in range(nb_segments):
            TransactionQueue._thread_queue.put((self._queue, self._exception))
        #
        # The threads run here until queue.join() returns, i.e. until
        # all add()ed transactions are executed.
        self._queue.join()
        #
        for i in range(nb_segments):
            self._queue.put((None, None, None))
        #
        if self._exception:
            exc_type, exc_value, exc_traceback = self._exception
            del self._exception
            raise exc_type, exc_value, exc_traceback

    #def number_of_transactions_executed(self):
    #    disabled for now

    @staticmethod
    def _thread_runner():
        while True:
            queue, exception = TransactionQueue._thread_queue.get()
            while True:
                f, args, kwds = queue.get()
                try:
                    if args is None:
                        break
                    with atomic:
                        if not exception:
                            try:
                                with signals_enabled:
                                    f(*args, **kwds)
                            except:
                                exception.extend(sys.exc_info())
                finally:
                    queue.task_done()


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
        self.tl_local = thread._local()

    def tl_wrefs(self):
        try:
            return self.tl_local.wrefs
        except AttributeError:
            self.tl_local.wrefs = wrefs = weakkeyiddict()
            return wrefs

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        wrefs = self.tl_wrefs()
        try:
            return wrefs[obj]
        except KeyError:
            if self.tl_default_factory is None:
                raise AttributeError
            wrefs[obj] = result = self.tl_default_factory()
            return result

    def __set__(self, obj, value):
        self.tl_wrefs()[obj] = value

    def __delete__(self, obj):
        try:
            del self.tl_wrefs()[obj]
        except KeyError:
            raise AttributeError
