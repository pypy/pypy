"""
A benchmark for read()
"""

import os

# __________  Entry point  __________

def entry_point(argv):
    length = 0
    if len(argv) > 1:
        length = int(argv[1])
    else:
        length = 100
    for i in xrange(100000):
        f = os.open(__file__, 0666, os.O_RDONLY)
        os.read(f, length)
        os.close(f)
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

