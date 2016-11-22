from rpython.rlib import jit, rstm, rthread


class Global(object):
    NUM_THREADS = 4
    LENGTH      = 5000
    node        = None

glob = Global()

class Node(object):
    def __init__(self, value, next):
        self.value = value
        self.next = next

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
        value = glob.LENGTH - 1 - value
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
        self.value = 0
        self.finished_lock = rthread.allocate_lock()
        self.finished_lock.acquire(True)

    def run(self):
        try:
            while self.value < glob.LENGTH:
                jitdriver.jit_merge_point(self=self)
                glob.node = Node(self.value, glob.node)
                self.value += 1
                if self.value % 10 == 0:
                    print self.index, ":", self.value
        finally:
            self.finished_lock.release()

jitdriver = jit.JitDriver(greens=[], reds=['self'])

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

    # def _freeze_(self):
    #     self.reinit()
    #     return False

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
        finally:
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
    except Exception:
        bootstrapper.release()     # normally called by the new thread
        raise
    return ident

# __________  Entry point  __________

def entry_point(argv):
    print "hello jit1 world"
    if len(argv) > 1:
        glob.NUM_THREADS = int(argv[1])
        if len(argv) > 2:
            glob.LENGTH = int(argv[2])
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
    check_chained_list(glob.node)
    #
    return 0

# _____ Define and setup target ___

from rpython.jit.codewriter.policy import JitPolicy

def jitpolicy(driver):
    return JitPolicy()

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    entry_point(sys.argv)
