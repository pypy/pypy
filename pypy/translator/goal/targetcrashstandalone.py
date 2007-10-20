"""
A simple standalone target.

The target below specifies None as the argument types list.
This is a case treated specially in driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""

import os, sys, weakref, gc
import pypy.rlib.rgc
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import lltype

def debug(msg): 
    os.write(2, "debug: " + msg + '\n')

# __________  Entry point  __________

class A:
    def __init__(self, i):
        self.i = i
def f(x):
    alist = [A(i) for i in range(x)]
    refarray = [None] * len(alist)
    # Compute the id of all elements of the list.  The goal is
    # to not allocate memory, so that if the GC needs memory to
    # remember the ids, it will trigger some collections itself
    i = 0
    while i < len(alist):
        refarray[i] = weakref.ref(alist[i])
        i += 1
    j = 0
    gc.collect()
    while j < 100:
        i = 0
        while i < len(alist):
            if refarray[i]() is not alist[i]:
                print "mismatch", j, i
                print refarray[i]().i
                llop.debug_print(lltype.Void, refarray[i], refarray[i](), type(refarray[i]()))
                print alist[i].i
                llop.debug_print(lltype.Void, alist[i], type(alist[i]))
                return
            i += 1
        j += 1
    print "match"
    return


def entry_point(argv):
    debug("hello world")
    f(int(argv[1]))
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
