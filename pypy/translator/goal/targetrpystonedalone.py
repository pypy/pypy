import os, sys
from pypy.translator.test import rpystone

# __________  Entry point  __________

def entry_point(argv):
    count = rpystone.pystones(20000000)
    return count

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

