import os, sys
from pypy.objspace.std.objspace import StdObjSpace
# XXX from pypy.annotation.model import *
# since we are execfile()'ed this would pull some
# weird objects into the globals, which we would try to pickle.
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef
from pypy.interpreter import gateway

# WARNING: this requires the annotator.
# There is no easy way to build all caches manually,
# but the annotator can do it for us for free.

this_dir = os.path.dirname(sys.argv[0])

# __________  Entry point  __________

def entry_point(argv):
    w_argv = space.newlist([space.wrap(s) for s in argv])
    w_exitcode = space.call(w_entry_point, w_argv)
    # try to pull it all in
##    from pypy.interpreter import main, interactive, error
##    con = interactive.PyPyConsole(space)
##    con.interact()
    return space.int_w(w_exitcode)

# _____ Define and setup target ___

def target():
    global space, w_entry_point
    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None
    # disable geninterp for now -- we have faaar toooo much interp-level code
    # for the poor translator already
    # XXX why can't I enable this? crashes the annotator!
    gateway.ApplevelClass.use_geninterp = False

    space = StdObjSpace()

    # manually imports app_main.py
    filename = os.path.join(this_dir, 'app_main.py')
    w_dict = space.newdict([])
    space.exec_(open(filename).read(), w_dict, w_dict)
    w_entry_point = space.getitem(w_dict, space.wrap('entry_point'))

    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    return entry_point, [s_list_of_strings]

# _____ Run translated _____
def run(c_entry_point):
    argv = [os.path.join(this_dir, 'app_example.py')]
    exitcode = c_entry_point(argv)
    assert exitcode == 0
