import os, sys

from pypy.tool.option import make_config

from pypy.objspace.logic import Space
# XXX from pypy.annotation.model import *
# since we are execfile()'ed this would pull some
# weird objects into the globals, which we would try to pickle.
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy

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

# _____ Define and setup target ___

opt_defaults = {'stackless' :  True}

take_options = True

def opt_parser():
    import py
    defl = {'thread': False, 'usemodules': ''}
    parser = py.compat.optparse.OptionParser(usage="target PyPy standalone", 
                                                add_help_option=False)
    parser.set_defaults(**defl)
    # XXX threading doesn't work
    #parser.add_option("--thread", action="store_true", dest="thread", 
    #                    help="enable threading")
    return parser

def print_help():
    opt_parser().print_help()

def target(driver, args):
    options = driver.options

    tgt_options, _ = opt_parser().parse_args(args)

    config = make_config(tgt_options)

    translate.log_options(tgt_options, "target PyPy options in effect")

    global space, w_entry_point

    if getattr(options, "lowmem", False):
        config.objspace.geninterp = False
    
    # obscure hack to stuff the translation options into the translated PyPy
    import pypy.module.sys
    wrapstr = 'space.wrap(%r)' % (options.__dict__)
    pypy.module.sys.Module.interpleveldefs['pypy_translation_info'] = wrapstr

    # disable translation of the whole of classobjinterp.py
    Space.setup_old_style_classes = lambda self: None

    config.objspace.nofaking = True
    config.objspace.compiler = "ast"
    config.translating = True
        
    # XXX threading is borken
    config.objspace.usemodules.thread = False
    config.objspace.usemodules._stackless = True

    space = Space(config)

    # manually imports app_main.py
    filename = os.path.join(this_dir, 'app_main.py')
    w_dict = space.newdict([])
    space.exec_(open(filename).read(), w_dict, w_dict)
    w_entry_point = space.getitem(w_dict, space.wrap('entry_point'))

    # sanity-check: call the entry point
    res = entry_point(["pypy", "app_basic_example.py"])
    assert res == 0

    return entry_point, None, PyPyAnnotatorPolicy()

