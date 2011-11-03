import time
from pypy.module.thread import ll_thread
from pypy.translator.stm import rstm


NUM_THREADS = 4
LENGTH      = 5000


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None


def add_at_end_of_chained_list(node, value):
    while node.next:
        node = node.next
    newnode = Node(value)
    node.next = newnode


class Global:
    anchor = Node(-1)
glob = Global()

def run_me():
    print "thread starting..."
    for i in range(LENGTH):
        add_at_end_of_chained_list(glob.anchor, i)
        rstm.transaction_boundary()
    print "thread done."
    glob.done += 1



# __________  temp, move me somewhere else  __________

from pypy.rlib.objectmodel import invoke_around_extcall

def before_external_call():
    # this function must not raise, in such a way that the exception
    # transformer knows that it cannot raise!
    rstm.commit_transaction()
before_external_call._gctransformer_hint_cannot_collect_ = True
before_external_call._dont_reach_me_in_del_ = True

def after_external_call():
    rstm.begin_inevitable_transaction()
after_external_call._gctransformer_hint_cannot_collect_ = True
after_external_call._dont_reach_me_in_del_ = True


# __________  Entry point  __________

def entry_point(argv):
    invoke_around_extcall(before_external_call, after_external_call)
    print "hello world"
    glob.done = 0
    for i in range(NUM_THREADS):
        ll_thread.start_new_thread(run_me, ())
    print "sleeping..."
    while glob.done < NUM_THREADS:    # poor man's lock
        time.sleep(1)
    print "done sleeping."
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
