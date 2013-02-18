print "warning: using transaction_emulator"

from collections import deque

pending = deque()

def add(f, *args):
    #print 'add:', f, args
    pending.append((f, args))

def run():
    while pending:
        f, args = pending.popleft()
        #print 'run:', f, args
        f(*args)

def set_num_threads(num):
    pass

def add_epoll(ep, callback):
    def poll_reader():
        # assume only one epoll is added.  If the _pending list is
        # now empty, wait.  If not, then just poll non-blockingly.
        if len(pending) == 0:
            timeout = -1
        else:
            timeout = 0
        got = ep.poll(timeout=timeout)
        for fd, events in got:
            add(callback, fd, events)
        add(poll_reader)
    add(poll_reader)
