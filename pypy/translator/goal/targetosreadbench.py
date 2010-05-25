"""
A benchmark for read()
"""

import os

# __________  Entry point  __________

def entry_point(argv):
    if len(argv) > 2:
        length = int(argv[1])
    else:
        length = 100
    fname = argv[1]
    for i in xrange(100000):
        f = os.open(fname, 0666, os.O_RDONLY)
        os.read(f, length)
        os.close(f)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

