import os, sys
from pypy.translator.test import rpystone

# __________  Entry point  __________

def entry_point(argv):
    count = rpystone.pystones(20000000)
    return count

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