from pypy.rpython.lltypesystem import rffi
from pypy.rlib import rstm
from pypy.rlib.debug import debug_print, ll_assert


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


def add_at_end_of_chained_list(node, value):
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


def _check_pointer(arg1):
    arg1.foobar = 40    # now 'arg1' is local
    return arg1

class CheckPointerEquality(rstm.Transaction):
    def __init__(self, arg):
        self.arg = arg
    def run(self):
        res = _check_pointer(self.arg)    # 'self.arg' reads a GLOBAL object
        ll_assert(res is self.arg, "ERROR: bogus pointer equality")
        raw1 = rffi.cast(rffi.CCHARP, self.retry_counter)
        raw2 = rffi.cast(rffi.CCHARP, -1)
        ll_assert(raw1 == raw2, "ERROR: retry_counter == -1")

class MakeChain(rstm.Transaction):
    def __init__(self, anchor, value):
        self.anchor = anchor
        self.value = value
    def run(self):
        add_at_end_of_chained_list(self.anchor, self.value)
        self.value += 1
        if self.value < glob.LENGTH:
            return [self]       # re-schedule the same Transaction object

class InitialTransaction(rstm.Transaction):
    def run(self):
        ll_assert(self.retry_counter == 0, "no reason to abort-and-retry here")
        scheduled = []
        for i in range(glob.NUM_THREADS):
            arg = Arg()
            arg.foobar = 41
            scheduled.append(CheckPointerEquality(arg))
            scheduled.append(MakeChain(glob.anchor, 0))
        return scheduled

# __________  Entry point  __________

def entry_point(argv):
    print "hello world"
    if len(argv) > 1:
        glob.NUM_THREADS = int(argv[1])
        if len(argv) > 2:
            glob.LENGTH = int(argv[2])
            if len(argv) > 3:
                glob.USE_MEMORY = bool(int(argv[3]))
    #
    rstm.run_all_transactions(InitialTransaction(),
                              num_threads=glob.NUM_THREADS)
    #
    check_chained_list(glob.anchor.next)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    entry_point(sys.argv)
