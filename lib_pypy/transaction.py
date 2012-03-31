import sys
import random


print >> sys.stderr, "warning: using lib_pypy/transaction.py, the emulator"

_pending = {}
_in_transaction = False


class TransactionError(Exception):
    pass


def set_num_threads(num):
    """Set the number of threads to use.  In a real implementation,
    the transactions will attempt to use 'num' threads in parallel.
    """


def add(f, *args, **kwds):
    """Register the call 'f(*args, **kwds)' as running a new
    transaction.  If we are currently running in a transaction too, the
    new transaction will only start after the end of the current
    transaction.  Note that if the same or another transaction raises an
    exception in the meantime, all pending transactions are cancelled.
    """
    r = random.random()
    assert r not in _pending    # very bad luck if it is
    _pending[r] = (f, args, kwds)


def add_epoll(ep, callback):
    """Register the epoll object (from the 'select' module).  For any
    event (fd, events) detected by 'ep', a new transaction will be
    started invoking 'callback(fd, events)'.  Note that all fds should
    be registered with the flag select.EPOLLONESHOT, and re-registered
    from the callback if needed.
    """
    for key, (f, args, kwds) in _pending.items():
        if getattr(f, '_reads_from_epoll_', None) is ep:
            raise TransactionError("add_epoll(ep): ep is already registered")
    def poll_reader():
        # assume only one epoll is added.  If the _pending list is
        # now empty, wait.  If not, then just poll non-blockingly.
        if len(_pending) == 0:
            timeout = -1
        else:
            timeout = 0
        got = ep.poll(timeout=timeout)
        for fd, events in got:
            add(callback, fd, events)
        add(poll_reader)
    poll_reader._reads_from_epoll_ = ep
    add(poll_reader)

def remove_epoll(ep):
    """Explicitly unregister the epoll object.  Note that raising an
    exception in a transaction to abort run() also unregisters all epolls.
    """
    for key, (f, args, kwds) in _pending.items():
        if getattr(f, '_reads_from_epoll_', None) is ep:
            del _pending[key]
            break
    else:
        raise TransactionError("remove_epoll(ep): ep is not registered")

def run():
    """Run the pending transactions, as well as all transactions started
    by them, and so on.  The order is random and undeterministic.  Must
    be called from the main program, i.e. not from within another
    transaction.  If at some point all transactions are done, returns.
    If a transaction raises an exception, it propagates here; in this
    case all pending transactions are cancelled.
    """
    global _pending, _in_transaction
    if _in_transaction:
        raise TransactionError("recursive invocation of transaction.run()")
    pending = _pending
    try:
        _in_transaction = True
        while pending:
            _, (f, args, kwds) = pending.popitem()
            f(*args, **kwds)
    finally:
        _in_transaction = False
        pending.clear()   # this is the behavior we get with interp_transaction
