"""
A simple standalone target.

The target below specifies None as the argument types list.
This is a case treated specially in driver.py . If the list
of input types is empty, it is meant to be a list of strings,
actually implementing argv of the executable.
"""

import os, sys

# __________  Entry point  __________

class A(object):
    pass

class B(object):
    pass

def f(x):
    b = B()
    b.x = x
    return b

global_a = A()

def entry_point(argv):
    # push argv
    global_a.b = f(len(argv))
    # pop argv
    return global_a.b.x

# _____ Define and setup target ___

def target(*args):
    return entry_point, None
