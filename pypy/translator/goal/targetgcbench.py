import os, sys
from pypy.translator.goal import gcbench

def entry_point(argv):
    if len(argv) > 1:
        n = int(argv[1])
    else:
        n = 1
    while n > 0:
        gcbench.main()
        n -= 1
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

"""
Why is this a stand-alone target?

The above target specifies None as the argument types list.
This is a case treated specially in the driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""
