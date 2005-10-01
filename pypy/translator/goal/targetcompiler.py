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

from pypy.translator.ann_override import PyPyAnnotatorPolicy

from pypy.interpreter.pyparser.pythonutil import target_ast_compile
from pypy.objspace.std.objspace import StdObjSpace

def entry_point( s1, s2 ):
    global space
    pycode = target_ast_compile( space, s1, s2 )
    return 'target_ast_compile --> %r' % (pycode,)

# _____ Define and setup target ___
def target(driver, args):
    options = driver.options

    global space, w_entry_point

    geninterp = not getattr(options, 'lowmem', False)
    
    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None
    # disable geninterp for now -- we have faaar toooo much interp-level code
    # for the poor translator already
    # XXX why can't I enable this? crashes the annotator!
    space = StdObjSpace(nofaking=True,
                        compiler="ast",
                        translating=True,
                        #usemodules=['marhsal', '_sre'],
                        geninterp=geninterp)
    return entry_point, [str, str], PyPyAnnotatorPolicy()

# _____ Run translated _____
def run(c_entry_point):
    pass
