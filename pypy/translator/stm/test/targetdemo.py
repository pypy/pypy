from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module.thread import ll_thread
from pypy.rlib import rstm, rgc
from pypy.rlib.debug import debug_print
from pypy.rpython.annlowlevel import llhelper


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
    pass


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


@rgc.no_collect     # don't use the gc as long as other threads are running
def _run():
    i = 0
    while i < glob.NUM_THREADS:
        glob._arg = glob._arglist[i]
        ll_run_me = llhelper(ll_thread.CALLBACK, run_me)
        ll_thread.c_thread_start_NOGIL(ll_run_me)
        ll_thread.acquire_NOAUTO(glob.lock, True)
        i += 1
    debug_print("sleeping...")
    while glob.done < glob.NUM_THREADS:    # poor man's lock
        _sleep(rffi.cast(rffi.ULONG, 1))
    debug_print("done sleeping.")


# Posix only
_sleep = rffi.llexternal('sleep', [rffi.ULONG], rffi.ULONG,
                         _nowrapper=True,
                         random_effects_on_gcobjs=False)


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
    ll_thread.acquire_NOAUTO(glob.lock, True)
    glob._arglist = [Arg() for i in range(glob.NUM_THREADS)]
    _run()
    check_chained_list(glob.anchor.next)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
