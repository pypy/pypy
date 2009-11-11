#!/usr/bin/env python

"""Main entry point into the PyPy interpreter.  For a list of options, type

      py.py --help

"""

try:
    import autopath
except ImportError:
    pass

from pypy.tool import option
from optparse import make_option
from pypy.interpreter import main, interactive, error, gateway
from pypy.config.config import OptionDescription, BoolOption, StrOption
from pypy.config.config import Config, to_optparse
from pypy.config import pypyoption
import os, sys
import time

cmdline_optiondescr = OptionDescription("interactive", "the options of py.py", [
    BoolOption("verbose", "show verbose interpreter-level traceback",
               default=os.getenv("PYPY_TB"), cmdline="-v"),
    BoolOption("interactive", "inspect interactively after running script",
               default=False, cmdline="-i"),
    BoolOption("completer", "use readline commandline completer",
               default=False, cmdline="-C"),
    BoolOption("optimize",
               "dummy optimization flag for compatibility with CPython",
               default=False, cmdline="-O"),
    BoolOption("no_site_import", "do not 'import site' on initialization",
               default=False, cmdline="-S"),
    StrOption("runmodule",
              "library module to be run as a script (terminates option list)",
              default=None, cmdline="-m"),
    StrOption("runcommand",
              "program passed in as CMD (terminates option list)",
              default=None, cmdline="-c"),
    StrOption("warn",
              "warning control (arg is action:message:category:module:lineno)",
              default=None, cmdline="-W"),
 
    ])

pypy_init = gateway.applevel('''
def pypy_init(import_site):
    if import_site:
        try:
            import site
        except:
            import sys
            print >> sys.stderr, "import site\' failed"
''').interphook('pypy_init')


def set_compiler(option, opt, value, parser):
    from pypy.translator.platform import set_platform
    set_platform('host', value)

def main_(argv=None):
    starttime = time.time()
    config, parser = option.get_standard_options()
    interactiveconfig = Config(cmdline_optiondescr)
    to_optparse(interactiveconfig, parser=parser)
    parser.add_option(
        '--cc', type=str, action="callback",
        callback=set_compiler,
        help="Compiler to use for compiling generated C")
    args = option.process_options(parser, argv[1:])
    if interactiveconfig.verbose:
        error.RECORD_INTERPLEVEL_TRACEBACK = True
    # --allworkingmodules takes really long to start up, but can be forced on
    config.objspace.suggest(allworkingmodules=False)
    if config.objspace.allworkingmodules:
        pypyoption.enable_allworkingmodules(config)

    # create the object space

    space = option.make_objspace(config)

    space._starttime = starttime
    space.setitem(space.sys.w_dict, space.wrap('executable'),
                  space.wrap(argv[0]))

    # set warning control options (if any)
    warn_arg = interactiveconfig.warn
    if warn_arg is not None:
        space.appexec([space.wrap(warn_arg)], """(arg): 
        import sys
        sys.warnoptions.append(arg)""")

    w_path = space.sys.get('path')
    path = os.getenv('PYTHONPATH')
    if path:
        path = path.split(os.pathsep)
    else:
        path = []
    path.insert(0, '')
    for i, dir in enumerate(path):
        space.call_method(w_path, 'insert', space.wrap(i), space.wrap(dir))

    # store the command-line arguments into sys.argv
    go_interactive = interactiveconfig.interactive
    banner = ''
    exit_status = 0
    if interactiveconfig.runcommand is not None:
        args = ['-c'] + args
    for arg in args:
        space.call_method(space.sys.get('argv'), 'append', space.wrap(arg))

    # load the source of the program given as command-line argument
    if interactiveconfig.runcommand is not None:
        def doit():
            main.run_string(interactiveconfig.runcommand, space=space)
    elif interactiveconfig.runmodule:
        def doit():
            main.run_module(interactiveconfig.runmodule,
                            args, space=space)
    elif args:
        scriptdir = os.path.dirname(os.path.abspath(args[0]))
        space.call_method(space.sys.get('path'), 'insert',
                          space.wrap(0), space.wrap(scriptdir))
        def doit():
            main.run_file(args[0], space=space)
    else:
        def doit():
            pass
        space.call_method(space.sys.get('argv'), 'append', space.wrap(''))
        go_interactive = 1
        banner = None

    try:
        def do_start():
            space.startup()
            pypy_init(space, space.wrap(not interactiveconfig.no_site_import))
        if main.run_toplevel(space, do_start,
                             verbose=interactiveconfig.verbose):
            # compile and run it
            if not main.run_toplevel(space, doit,
                                     verbose=interactiveconfig.verbose):
                exit_status = 1

            # start the interactive console
            if go_interactive or os.getenv('PYTHONINSPECT'):
                try:
                    import readline
                except:
                    pass
                con = interactive.PyPyConsole(
                    space, verbose=interactiveconfig.verbose,
                    completer=interactiveconfig.completer)
                if banner == '':
                    banner = '%s / %s'%(con.__class__.__name__,
                                        repr(space))
                con.interact(banner)
                exit_status = 0
    finally:
        def doit():
            space.finish()
        main.run_toplevel(space, doit, verbose=interactiveconfig.verbose)

    return exit_status


if __name__ == '__main__':
    if hasattr(sys, 'setrecursionlimit'):
        # for running "python -i py.py -Si -- py.py -Si" 
        sys.setrecursionlimit(3000)
    sys.exit(main_(sys.argv))
