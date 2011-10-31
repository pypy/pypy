import time
from pypy.module.thread import ll_thread
from pypy.translator.stm import rstm


NUM_THREADS = 4
LENGTH      = 1000


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


# __________  Entry point  __________

def entry_point(argv):
    print "hello world"
    for i in range(NUM_THREADS):
        ll_thread.start_new_thread(run_me, ())
    time.sleep(10)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
