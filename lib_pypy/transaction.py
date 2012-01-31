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
    add(poll_reader)

def run():
    pending = _pending
    while pending:
        _, (f, args) = pending.popitem()
        f(*args)
