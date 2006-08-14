import os, sys

from pypy.tool.option import make_config

from pypy.objspace.std.objspace import StdObjSpace
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

# _____ Define and setup target ___

# for now this will do for option handling

take_options = True

def opt_parser():
    import py
    defl = {'thread': False}
    parser = py.compat.optparse.OptionParser(usage="target multiple spaces", 
                                                add_help_option=False)
    parser.set_defaults(**defl)
    parser.add_option("--thread", action="store_true", dest="thread", 
                        help="enable threading")
    parser.add_option("--usemodules", action="store", type="string", 
                        dest="usemodules", help=("list of mixed modules to "
                                            "include, comma-separated"))
    return parser

def print_help():
    opt_parser().print_help()


def target(driver, args):
    options = driver.options

    tgt_options, _ = opt_parser().parse_args(args)

    config = make_config(tgt_options)

    translate.log_options(tgt_options, "target PyPy options in effect")

    options.thread = tgt_options.thread

    global space1, space2, w_entry_point_1, w_entry_point_2

    if getattr(options, "lowmem", False):
        config.objspace.geninterp = False
    
    # obscure hack to stuff the translation options into the translated PyPy
    import pypy.module.sys
    wrapstr = 'space.wrap(%r)' % (options.__dict__)
    pypy.module.sys.Module.interpleveldefs['pypy_translation_info'] = wrapstr

    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None

    usemodules = []
    if tgt_options.usemodules:
        for modname in tgt_options.usemodules.split(","):
            setattr(config.objspace.usemodules, modname, True)
    if tgt_options.thread:
        print "threads unsupported right now: need thread-safe stack_too_big"
        raise SystemExit        
        config.objspace.usemodules.thread = True
    if options.stackless:
        config.objspace.usemodules._stackless = True
    config.objspace.nofaking = True
    config.objspace.compiler = "ast"
    config.translating = True

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

    # sanity-check: call the entry point
    res = entry_point(["pypy", "app_basic_example.py"])
    assert res == 0
    res = entry_point(["pypy", "--space2", "app_basic_example.py"])
    assert res == 0

    return entry_point, None, PyPyAnnotatorPolicy()

