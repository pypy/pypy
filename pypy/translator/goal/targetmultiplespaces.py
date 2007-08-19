import os, sys

from pypy.objspace.std.objspace import StdObjSpace
# XXX from pypy.annotation.model import *
# since we are execfile()'ed this would pull some
# weird objects into the globals, which we would try to pickle.
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
from pypy.translator.goal.targetpypystandalone import PyPyTarget, debug

# WARNING: this requires the annotator.
# There is no easy way to build all caches manually,
# but the annotator can do it for us for free.

try:
    this_dir = os.path.dirname(__file__)
except NameError:
    this_dir = os.path.dirname(sys.argv[0])

def debug(msg): 
    os.write(2, "debug: " + msg + '\n')

# __________  Entry point  __________

def entry_point(argv):
    debug("entry point starting") 
    for arg in argv: 
        debug(" argv -> " + arg)
    if len(argv) > 1 and argv[1] == "--space2":
        del argv[1]
        space = space2
        w_entry_point = w_entry_point_2
    else:
        space = space1
        w_entry_point = w_entry_point_1
    try:
        w_executable = space.wrap(argv[0])
        w_argv = space.newlist([space.wrap(s) for s in argv[1:]])
        w_exitcode = space.call_function(w_entry_point, w_executable, w_argv)
        # try to pull it all in
    ##    from pypy.interpreter import main, interactive, error
    ##    con = interactive.PyPyConsole(space)
    ##    con.interact()
    except OperationError, e:
        debug("OperationError:")
        debug(" operror-type: " + e.w_type.getname(space, '?'))
        debug(" operror-value: " + space.str_w(space.str(e.w_value)))
        return 1
    return space.int_w(w_exitcode)


class MultipleSpaceTarget(PyPyTarget):
    
    usage = "target multiple spaces standalone"

    def handle_config(self, config):
        config.set(**{"translation.thread": False})

    def get_entry_point(self, config):
        global space1, space2, w_entry_point_1, w_entry_point_2
        space1 = StdObjSpace(config)
        space2 = StdObjSpace(config)

        space1.setattr(space1.getbuiltinmodule('sys'),
                       space1.wrap('pypy_space'),
                       space1.wrap(1))
        space2.setattr(space2.getbuiltinmodule('sys'),
                       space2.wrap('pypy_space'),
                       space2.wrap(2))

        # manually imports app_main.py
        filename = os.path.join(this_dir, 'app_main.py')
        w_dict = space1.newdict()
        space1.exec_(open(filename).read(), w_dict, w_dict)
        w_entry_point_1 = space1.getitem(w_dict, space1.wrap('entry_point'))

        w_dict = space2.newdict()
        space2.exec_(open(filename).read(), w_dict, w_dict)
        w_entry_point_2 = space2.getitem(w_dict, space2.wrap('entry_point'))

        return entry_point, None, PyPyAnnotatorPolicy()


MultipleSpaceTarget().interface(globals())
