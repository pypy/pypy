import os, sys
from pypy.annotation.model import *
from pypy.annotation.listdef import ListDef

# WARNING: this requires the annotator.
# There is no easy way to build all caches manually,
# but the annotator can do it for us for free.

this_dir = os.path.dirname(sys.argv[0])

# from pypy.interpreter.pyparser.pythonutil import annotateme
# __________  Entry point  __________
# entry_point = annotateme

from pypy.interpreter.pyparser.pythonutil import target_ast_compile
from pypy.objspace.std.objspace import StdObjSpace

def entry_point( s1, s2 ):
    global space
    return target_ast_compile( space, s1, s2 )

# _____ Define and setup target ___
def target():
    global space, w_entry_point
    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None
    # disable geninterp for now -- we have faaar toooo much interp-level code
    # for the poor translator already
    # XXX why can't I enable this? crashes the annotator!
    space = StdObjSpace(nofaking=True,
                        compiler="astparser",
                        translating=True,
                        #usemodules=['marhsal', '_sre'],
                        geninterp=False)
    return entry_point, [str, str]

# _____ Run translated _____
def run(c_entry_point):
    pass
