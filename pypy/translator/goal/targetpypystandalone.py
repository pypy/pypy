import os, sys

# as of revision 27081, multimethod.py uses the InstallerVersion1 by default
# because it is much faster both to initialize and run on top of CPython.
# The InstallerVersion2 is optimized for making a translator-friendly
# structure.  So we patch here...
from pypy.objspace.std import multimethod
multimethod.Installer = multimethod.InstallerVersion2

from pypy.objspace.std.objspace import StdObjSpace
# XXX from pypy.annotation.model import *
# since we are execfile()'ed this would pull some
# weird objects into the globals, which we would try to pickle.
from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy

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
        try:
            space.call_function(w_run_toplevel, w_call_startup)
            w_executable = space.wrap(argv[0])
            w_argv = space.newlist([space.wrap(s) for s in argv[1:]])
            w_exitcode = space.call_function(w_entry_point, w_executable, w_argv)
            exitcode = space.int_w(w_exitcode)
            # try to pull it all in
        ##    from pypy.interpreter import main, interactive, error
        ##    con = interactive.PyPyConsole(space)
        ##    con.interact()
        except OperationError, e:
            debug("OperationError:")
            debug(" operror-type: " + e.w_type.getname(space, '?'))
            debug(" operror-value: " + space.str_w(space.str(e.w_value)))
            return 1
    finally:
        try:
            space.call_function(w_run_toplevel, w_call_finish)
        except OperationError, e:
            debug("OperationError:")
            debug(" operror-type: " + e.w_type.getname(space, '?'))
            debug(" operror-value: " + space.str_w(space.str(e.w_value)))
            return 1
    return exitcode

# _____ Define and setup target ___

# for now this will do for option handling

take_options = True

def opt_parser():
    import py
    defl = {'thread': False, 'usemodules': ''}
    parser = py.compat.optparse.OptionParser(usage="target PyPy standalone", add_help_option=False)
    parser.set_defaults(**defl)
    parser.add_option("--thread", action="store_true", dest="thread", help="enable threading")
    parser.add_option("--usemodules", action="store", type="string", dest="usemodules",
            help="list of mixed modules to include, comma-separated")
    return parser

def print_help():
    opt_parser().print_help()


def call_finish(space):
    space.finish()

w_call_finish = gateway.interp2app(call_finish)

def call_startup(space):
    space.startup()

w_call_startup = gateway.interp2app(call_startup)



def target(driver, args):
    driver.exe_name = 'pypy-%(backend)s'
    options = driver.options

    tgt_options, _ = opt_parser().parse_args(args)

    translate.log_options(tgt_options, "target PyPy options in effect")

    global space, w_entry_point, w_run_toplevel

    geninterp = not getattr(options, 'lowmem', False)
    
    # obscure hack to stuff the translation options into the translated PyPy
    import pypy.module.sys
    wrapstr = 'space.wrap(%r)' % (options.__dict__)
    pypy.module.sys.Module.interpleveldefs['pypy_translation_info'] = wrapstr

    # disable translation of the whole of classobjinterp.py
    StdObjSpace.setup_old_style_classes = lambda self: None

    usemodules = []
    if tgt_options.usemodules:
        usemodules.extend(tgt_options.usemodules.split(","))
    if tgt_options.thread:
        # thread might appear twice now, but the objspace can handle this
        usemodules.append('thread')
    if options.stackless:
        usemodules.append('stackless')
        
    space = StdObjSpace(nofaking=True,
                        compiler="ast", # interpreter/astcompiler
                        translating=True,
                        usemodules=usemodules,
                        geninterp=geninterp)
    # manually imports app_main.py
    filename = os.path.join(this_dir, 'app_main.py')
    w_dict = space.newdict([])
    space.exec_(open(filename).read(), w_dict, w_dict)
    w_entry_point = space.getitem(w_dict, space.wrap('entry_point'))
    w_run_toplevel = space.getitem(w_dict, space.wrap('run_toplevel'))

    # sanity-check: call the entry point
    res = entry_point(["pypy", "app_basic_example.py"])
    assert res == 0

    return entry_point, None, PyPyAnnotatorPolicy(single_space = space)

