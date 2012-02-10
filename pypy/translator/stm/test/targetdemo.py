import time
from pypy.module.thread import ll_thread
from pypy.rlib import rstm
from pypy.rlib.debug import debug_print


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

class Global:
    NUM_THREADS = 4
    LENGTH      = 5000
    USE_MEMORY  = False
    anchor      = Node(-1)
glob = Global()

class Arg:
    _alloc_nonmovable_ = True     # XXX kill me


def add_at_end_of_chained_list(arg, retry_counter):
    assert arg.foobar == 42
    node = arg.anchor
    value = arg.value
    x = Node(value)
    while node.next:
        node = node.next
        if glob.USE_MEMORY:
            x = Node(value)
    newnode = x
    node.next = newnode

def check_chained_list(node):
    seen = [0] * (glob.LENGTH+1)
    seen[-1] = glob.NUM_THREADS
    errors = glob.LENGTH
    while node is not None:
        value = node.value
        #print value
        if not (0 <= value < glob.LENGTH):
            print "node.value out of bounds:", value
            raise AssertionError
        seen[value] += 1
        if seen[value] > seen[value-1]:
            errors = min(errors, value)
        node = node.next
    if errors < glob.LENGTH:
        value = errors
        print "seen[%d] = %d, seen[%d] = %d" % (value-1, seen[value-1],
                                                value, seen[value])
        raise AssertionError

    if seen[glob.LENGTH-1] != glob.NUM_THREADS:
        print "seen[LENGTH-1] != NUM_THREADS"
        raise AssertionError
    print "check ok!"


def increment_done(arg, retry_counter):
    print "thread done."
    glob.done += 1

def run_me():
    rstm.descriptor_init()
    try:
        debug_print("thread starting...")
        arg = glob._arg
        ll_thread.release_NOAUTO(glob.lock)
        arg.foobar = 41
        i = 0
        while i < glob.LENGTH:
            arg.anchor = glob.anchor
            arg.value = i
            arg.foobar = 42
            rstm.perform_transaction(add_at_end_of_chained_list, Arg, arg)
            i += 1
        rstm.perform_transaction(increment_done, Arg, arg)
    finally:
        rstm.descriptor_done()


# __________  Entry point  __________

def entry_point(argv):
    print "hello world"
    if len(argv) > 1:
        glob.NUM_THREADS = int(argv[1])
        if len(argv) > 2:
            glob.LENGTH = int(argv[2])
            if len(argv) > 3:
                glob.USE_MEMORY = bool(int(argv[3]))
    glob.done = 0
    glob.lock = ll_thread.allocate_ll_lock()
    ll_thread.acquire_NOAUTO(glob.lock, 1)
    for i in range(glob.NUM_THREADS):
        glob._arg = Arg()
        ll_thread.start_new_thread(run_me, ())
        ll_thread.acquire_NOAUTO(glob.lock, 1)
    print "sleeping..."
    while glob.done < glob.NUM_THREADS:    # poor man's lock
        time.sleep(1)
    print "done sleeping."
    check_chained_list(glob.anchor.next)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
