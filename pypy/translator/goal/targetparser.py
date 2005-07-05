import os, sys
from pypy.annotation.model import *
from pypy.annotation.listdef import ListDef

# WARNING: this requires the annotator.
# There is no easy way to build all caches manually,
# but the annotator can do it for us for free.

this_dir = os.path.dirname(sys.argv[0])

from pypy.interpreter.pyparser.pythonutil import annotateme
# __________  Entry point  __________
entry_point = annotateme

# _____ Define and setup target ___
def target():
    return entry_point, [str]

# _____ Run translated _____
def run(c_entry_point):
    pass
