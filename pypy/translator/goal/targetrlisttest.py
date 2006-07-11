from pypy.rpython.objectmodel import r_dict
import os, sys
import operator
import time

# __________  Entry point  __________

N_ITEMS = 100000000

def entry_point(argv):
    lst = range(N_ITEMS)
    lst[0] = 1
    start = time.time()
    lst.index(N_ITEMS-1)
    end = time.time()
    os.write(1, 'Time elapsed: %s\n' % (end-start))
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

