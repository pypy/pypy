import sys
import random


print >> sys.stderr, "warning: using lib_pypy/transaction.py, the emulator"

_pending = {}

def set_num_threads(num):
    pass

def add(f, *args):
    r = random.random()
    assert r not in _pending    # very bad luck if it is
    _pending[r] = (f, args)

def add_epoll(ep, callback):
    for key, (f, args) in _pending.items():
        if getattr(f, '_reads_from_epoll_', None) is ep:
            raise ValueError("add_epoll(ep): ep is already registered")
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
    for key, (f, args) in _pending.items():
        if getattr(f, '_reads_from_epoll_', None) is ep:
            del _pending[key]
            break
    else:
        raise ValueError("remove_epoll(ep): ep is not registered")

def run():
    pending = _pending
    try:
        while pending:
            _, (f, args) = pending.popitem()
            f(*args)
    finally:
        pending.clear()   # this is the behavior we get with interp_transaction
