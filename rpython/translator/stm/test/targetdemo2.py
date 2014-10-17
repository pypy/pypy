import time
from rpython.rlib import rthread
from rpython.rlib import rstm
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.objectmodel import compute_identity_hash
from rpython.rlib.debug import ll_assert
from rpython.rtyper.lltypesystem import lltype, rffi, rclass


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

class Global:
    NUM_THREADS = 4
    LENGTH      = 5000
    USE_MEMORY  = False
    anchor      = Node(-1)
    othernode1  = Node(0)
    othernode1hash = compute_identity_hash(othernode1)
    othernode2  = Node(0)
    othernode2hash = 0
    othernodes  = [Node(0) for i in range(1000)]
glob = Global()

STRUCT = lltype.GcStruct('STRUCT', ('x', lltype.Signed))

def add_at_end_of_chained_list(node, value, threadindex):
    x = Node(value)
    while node.next:
        node = node.next
        if glob.USE_MEMORY:
            x = Node(value)
    if not we_are_translated():
        print threadindex
        time.sleep(0.01)
    newnode = x
    assert node.next is None
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


class ThreadRunner(object):
    arg = None

    def __init__(self, i):
        self.index = i
        self.finished_lock = rthread.allocate_lock()
        self.finished_lock.acquire(True)

    def run(self):
        try:
            self.lst = []
            self.do_check_hash()
            self.do_check_inev()
            self.arg = Arg()
            self.glob_p = lltype.malloc(STRUCT)
            self.do_check_ptr_equality()
            self.do_run_really()
        finally:
            self.finished_lock.release()

    def do_run_really(self):
        value = 0
        while True:
            rstm.possible_transaction_break(True)
            if not self.run_really(value):
                break
            value += 1

    def run_really(self, value):
        if value == glob.LENGTH // 2:
            print "atomic!"
            assert not rstm.is_atomic()
            rstm.increment_atomic()
            assert rstm.is_atomic()
        if value == glob.LENGTH * 2 // 3:
            print "--------------- done atomic"
            assert rstm.is_atomic()
            rstm.decrement_atomic()
            assert not rstm.is_atomic()
        #
        add_at_end_of_chained_list(glob.anchor, value, self.index)
        return (value+1) < glob.LENGTH

    def do_check_ptr_equality(self):
        rstm.possible_transaction_break(True)
        self.check_ptr_equality(0)

    def check_ptr_equality(self, foo):
        assert self.glob_p != lltype.nullptr(STRUCT)
        res = _check_pointer(self.arg)    # 'self.arg' reads a GLOBAL object
        ll_assert(res is self.arg, "ERROR: bogus pointer equality")
        raw1 = rffi.cast(rffi.CCHARP, foo)
        raw2 = rffi.cast(rffi.CCHARP, -1)
        ll_assert(raw1 != raw2, "ERROR: foo == -1")

    def do_check_inev(self):
        value = 0
        while True:
            rstm.possible_transaction_break(True)
            if not self.check_inev(value):
                break
            value += 1

    def _check_content(self, content):
        ll_assert(glob.othernode2.value == content, "bogus value after inev")
    _check_content._dont_inline_ = True

    def _check_inev(self):
        read_value = glob.othernode1.value
        rstm.become_inevitable()
        self._check_content(read_value)
    _check_inev._dont_inline_ = True

    def check_inev(self, value):
        value += 1
        new_value = self.index * 1000000 + value
        self._check_inev()
        glob.othernode1.value = new_value
        for n in glob.othernodes:   # lots of unrelated writes in-between
            n.value = new_value
        glob.othernode2.value = new_value
        return value < glob.LENGTH

    def do_check_hash(self):
        value = 0
        while True:
            rstm.possible_transaction_break(True)
            value = self.check_hash(value)
            if value >= glob.LENGTH:
                break

    def check_hash(self, value):
        if value == 0:
            glob.othernode2hash = compute_identity_hash(glob.othernode2)
        assert glob.othernode1hash == compute_identity_hash(glob.othernode1)
        assert glob.othernode2hash == compute_identity_hash(glob.othernode2)
        x = Node(0)
        lst = self.lst
        lst.append((x, compute_identity_hash(x)))
        for i in range(len(lst)):
            x, expected_hash = lst[i]
            assert compute_identity_hash(x) == expected_hash
            if i % 7 == 0:
                x.value += 1
            assert compute_identity_hash(x) == expected_hash
        value += 20
        return value

class Arg:
    foobar = 42

def _check_pointer(arg1):
    arg1.foobar = 40    # now 'arg1' is local
    return arg1

# ____________________________________________________________
# bah, we are really missing an RPython interface to threads

class Bootstrapper(object):
    # The following lock is held whenever the fields
    # 'bootstrapper.w_callable' and 'bootstrapper.args' are in use.
    lock = None
    args = None

    @staticmethod
    def setup():
        if bootstrapper.lock is None:
            bootstrapper.lock = rthread.allocate_lock()

    @staticmethod
    def reinit():
        bootstrapper.lock = None
        bootstrapper.args = None

    def _cleanup_(self):
        self.reinit()

    @staticmethod
    def bootstrap():
        # Note that when this runs, we already hold the GIL.  This is ensured
        # by rffi's callback mecanism: we are a callback for the
        # c_thread_start() external function.
        rthread.gc_thread_start()
        args = bootstrapper.args
        bootstrapper.release()
        # run!
        try:
            args.run()
        except Exception, e:
            # argh
            try:
                print "Got an exception from bootstrap()"
                if not we_are_translated():
                    print e.__class__.__name__, e
            except Exception:
                pass
        rthread.gc_thread_die()

    @staticmethod
    def acquire(args):
        # If the previous thread didn't start yet, wait until it does.
        # Note that bootstrapper.lock must be a regular lock, not a NOAUTO
        # lock, because the GIL must be released while we wait.
        bootstrapper.lock.acquire(True)
        bootstrapper.args = args

    @staticmethod
    def release():
        # clean up 'bootstrapper' to make it ready for the next
        # start_new_thread() and release the lock to tell that there
        # isn't any bootstrapping thread left.
        bootstrapper.args = None
        bootstrapper.lock.release()

bootstrapper = Bootstrapper()

def setup_threads():
    #space.threadlocals.setup_threads(space)
    bootstrapper.setup()

def start_thread(args):
    bootstrapper.acquire(args)
    try:
        ident = rthread.start_new_thread(bootstrapper.bootstrap, ())
    except Exception, e:
        bootstrapper.release()     # normally called by the new thread
        raise
    return ident

# __________  Entry point  __________

def entry_point(argv):
    print "hello 2nd world"
    if len(argv) > 1:
        glob.NUM_THREADS = int(argv[1])
        if len(argv) > 2:
            glob.LENGTH = int(argv[2])
            if len(argv) > 3:
                glob.USE_MEMORY = bool(int(argv[3]))
    #
    setup_threads()
    #
    locks = []
    for i in range(glob.NUM_THREADS):
        threadrunner = ThreadRunner(i)
        start_thread(threadrunner)
        locks.append(threadrunner.finished_lock)
    for lock in locks:
        lock.acquire(True)
    #
    check_chained_list(glob.anchor.next)
    #
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    entry_point(sys.argv)
