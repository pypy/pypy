#! /usr/bin/env python
# App-level version of py.py.
# See test/test_app_main.
"""
options:
  -i             inspect interactively after running script
  -O             dummy optimization flag for compatibility with C Python
  -c CMD         program passed in as CMD (terminates option list)
  -S             do not 'import site' on initialization
  -u             unbuffered binary stdout and stderr
  -h, --help     show this help message and exit
  -m             library module to be run as a script (terminates option list)
  -W arg         warning control (arg is action:message:category:module:lineno)
  --version      print the PyPy version
  --info         print translation information about this PyPy executable
"""

import sys

DEBUG = False       # dump exceptions before calling the except hook

originalexcepthook = sys.__excepthook__

def run_toplevel(f, *fargs, **fkwds):
    """Calls f() and handles all OperationErrors.
    Intended use is to run the main program or one interactive statement.
    run_protected() handles details like forwarding exceptions to
    sys.excepthook(), catching SystemExit, printing a newline after
    sys.stdout if needed, etc.
    """
    try:
        # run it
        f(*fargs, **fkwds)

        # we arrive here if no exception is raised.  stdout cosmetics...
        try:
            stdout = sys.stdout
            softspace = stdout.softspace
        except AttributeError:
            pass
            # Don't crash if user defined stdout doesn't have softspace
        else:
            if softspace:
                stdout.write('\n')

    except SystemExit, e:
        # exit if we catch a w_SystemExit
        exitcode = e.code
        if exitcode is None:
            exitcode = 0
        else:
            try:
                exitcode = int(exitcode)
            except:
                # not an integer: print it to stderr
                try:
                    stderr = sys.stderr
                except AttributeError:
                    pass   # too bad
                else:
                    print >> stderr, exitcode
                exitcode = 1
        raise SystemExit(exitcode)

    except:
        etype, evalue, etraceback = sys.exc_info()
        try:
            # extra debugging info in case the code below goes very wrong
            if DEBUG and hasattr(sys, 'stderr'):
                s = getattr(etype, '__name__', repr(etype))
                print >> sys.stderr, "debug: exception-type: ", s
                print >> sys.stderr, "debug: exception-value:", str(evalue)
                tbentry = etraceback
                if tbentry:
                    while tbentry.tb_next:
                        tbentry = tbentry.tb_next
                    lineno = tbentry.tb_lineno
                    filename = tbentry.tb_frame.f_code.co_filename
                    print >> sys.stderr, "debug: exception-tb:    %s:%d" % (
                        filename, lineno)

            # set the sys.last_xxx attributes
            sys.last_type = etype
            sys.last_value = evalue
            sys.last_traceback = etraceback

            # call sys.excepthook
            hook = getattr(sys, 'excepthook', originalexcepthook)
            hook(etype, evalue, etraceback)
            return False   # done

        except:
            try:
                stderr = sys.stderr
            except AttributeError:
                pass   # too bad
            else:
                print >> stderr, 'Error calling sys.excepthook:'
                originalexcepthook(*sys.exc_info())
                print >> stderr
                print >> stderr, 'Original exception was:'

        # we only get here if sys.excepthook didn't do its job
        originalexcepthook(etype, evalue, etraceback)
        return False

    return True   # success

# ____________________________________________________________
# Option parsing

def print_info():
    try:
        options = sys.pypy_translation_info
    except AttributeError:
        print >> sys.stderr, 'no translation information found'
    else:
        optitems = options.items()
        optitems.sort()
        for name, value in optitems:
            print ' %51s: %s' % (name, value)

def print_help():
    print 'usage: %s [options]' % (sys.executable,)
    print __doc__.rstrip()
    if 'pypyjit' in sys.builtin_module_names:
        print_jit_help()
    print

def print_jit_help():
    import pypyjit
    items = pypyjit.defaults.items()
    items.sort()
    for key, value in items:
        print '  --jit %s=N %slow-level JIT parameter (default %s)' % (
            key, ' '*(18-len(key)), value)

class CommandLineError(Exception):
    pass

def print_error(msg):
    print >> sys.stderr, msg
    print >> sys.stderr, 'usage: %s [options]' % (sys.executable,)
    print >> sys.stderr, 'Try `%s -h` for more information.' % (sys.executable,)

def set_unbuffered_io():
    sys.stdin  = sys.__stdin__  = os.fdopen(0, 'rb', 0)
    sys.stdout = sys.__stdout__ = os.fdopen(1, 'wb', 0)
    sys.stderr = sys.__stderr__ = os.fdopen(2, 'wb', 0)

def set_fully_buffered_io():
    sys.stdout = sys.__stdout__ = os.fdopen(1, 'w')

# ____________________________________________________________
# Main entry point

# see nanos.py for explainment why we do not import os here
# CAUTION!
# remember to update nanos.py if you are using more functions
# from os or os.path!
# Running test/test_nanos.py might be helpful as well.

def we_are_translated():
    # app-level, very different from pypy.rlib.objectmodel.we_are_translated
    return hasattr(sys, 'pypy_translation_info')

if 'nt' in sys.builtin_module_names:
    IS_WINDOWS = True
    DRIVE_LETTER_SEP = ':'
else:
    IS_WINDOWS = False

def get_argument(option, argv, i):
    arg = argv[i]
    n = len(option)
    if len(arg) > n:
        return arg[n:], i
    else:
        i += 1
        if i >= len(argv):
            raise CommandLineError('Argument expected for the %s option' %
                                   option)
        return argv[i], i


def setup_initial_paths(executable, nanos):
    # a substituted os if we are translated
    global os
    os = nanos
    AUTOSUBPATH = 'share' + os.sep + 'pypy-%d.%d'
    # find the full path to the executable, assuming that if there is no '/'
    # in the provided one then we must look along the $PATH
    if we_are_translated() and IS_WINDOWS and not executable.lower().endswith('.exe'):
        executable += '.exe'
    if os.sep in executable or (IS_WINDOWS and DRIVE_LETTER_SEP in executable):
        pass    # the path is already more than just an executable name
    else:
        path = os.getenv('PATH')
        if path:
            for dir in path.split(os.pathsep):
                fn = os.path.join(dir, executable)
                if os.path.isfile(fn):
                    executable = fn
                    break
    sys.executable = os.path.abspath(executable)

    # set up a sys.path that depends on the local machine
    autosubpath = AUTOSUBPATH % sys.pypy_version_info[:2]
    search = executable
    while 1:
        dirname = resolvedirof(search)
        if dirname == search:
            # not found!  let's hope that the compiled-in path is ok
            print >> sys.stderr, ('debug: WARNING: library path not found, '
                                  'using compiled-in sys.path')
            newpath = sys.path[:]
            break
        newpath = sys.pypy_initial_path(dirname)
        if newpath is None:
            newpath = sys.pypy_initial_path(os.path.join(dirname, autosubpath))
            if newpath is None:
                search = dirname    # walk to the parent directory
                continue
        break      # found!
    path = os.getenv('PYTHONPATH')
    if path:
        newpath = path.split(os.pathsep) + newpath
    newpath.insert(0, '')
    # remove duplicates
    _seen = {}
    del sys.path[:]
    for dir in newpath:
        if dir not in _seen:
            sys.path.append(dir)
            _seen[dir] = True
    return executable


def parse_command_line(argv):
    go_interactive = False
    run_command = False
    import_site = True
    i = 0
    run_module = False
    run_stdin = False
    warnoptions = []
    unbuffered = False
    while i < len(argv):
        arg = argv[i]
        if not arg.startswith('-'):
            break
        if arg == '-i':
            go_interactive = True
        elif arg.startswith('-c'):
            cmd, i = get_argument('-c', argv, i)
            argv[i] = '-c'
            run_command = True
            break
        elif arg == '-u':
            unbuffered = True
        elif arg == '-O':
            pass
        elif arg == '--version' or arg == '-V':
            print "Python", sys.version
            return
        elif arg == '--info':
            print_info()
            return
        elif arg == '-h' or arg == '--help':
            print_help()
            return
        elif arg == '-S':
            import_site = False
        elif arg == '-':
            run_stdin = True
            break     # not an option but a file name representing stdin
        elif arg.startswith('-m'):
            module, i = get_argument('-m', argv, i)
            argv[i] = module
            run_module = True
            break
        elif arg.startswith('-W'):
            warnoptions, i = get_argument('-W', argv, i)
        elif arg.startswith('--jit'):
            jitparam, i = get_argument('--jit', argv, i)
            if 'pypyjit' not in sys.builtin_module_names:
                print >> sys.stderr, ("Warning: No jit support in %s" %
                                      (sys.executable,))
            else:
                import pypyjit
                pypyjit.set_param(jitparam)
        elif arg == '--':
            i += 1
            break     # terminates option list    
        else:
            raise CommandLineError('unrecognized option %r' % (arg,))
        i += 1
    sys.argv = argv[i:]
    if not sys.argv:
        sys.argv.append('')
        run_stdin = True
    return locals()

def run_command_line(go_interactive,
                     run_command,
                     import_site,
                     run_module,
                     run_stdin,
                     warnoptions,
                     unbuffered,
                     cmd=None,
                     **ignored):
    # with PyPy in top of CPython we can only have around 100 
    # but we need more in the translated PyPy for the compiler package 
    sys.setrecursionlimit(5000)

    if unbuffered:
        set_unbuffered_io()
    elif not sys.stdout.isatty():
        set_fully_buffered_io()


    mainmodule = type(sys)('__main__')
    sys.modules['__main__'] = mainmodule

    if import_site:
        try:
            import site
        except:
            print >> sys.stderr, "'import site' failed"

    if warnoptions:
        sys.warnoptions.append(warnoptions)
        from warnings import _processoptions
        _processoptions(sys.warnoptions)

    # set up the Ctrl-C => KeyboardInterrupt signal handler, if the
    # signal module is available
    try:
        import signal
    except ImportError:
        pass
    else:
        signal.signal(signal.SIGINT, signal.default_int_handler)
        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        if hasattr(signal, 'SIGXFZ'):
            signal.signal(signal.SIGXFZ, signal.SIG_IGN)
        if hasattr(signal, 'SIGXFSZ'):
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)

    def inspect_requested():
        # We get an interactive prompt in one of the following two cases:
        #
        #     * go_interactive=True, either from the "-i" option or
        #       from the fact that we printed the banner;
        # or
        #     * PYTHONINSPECT is set and stdin is a tty.
        #
        return (go_interactive or
                (os.getenv('PYTHONINSPECT') and sys.stdin.isatty()))

    success = True

    try:
        if run_command:
            # handle the "-c" command
            def run_it():
                exec cmd in mainmodule.__dict__
            success = run_toplevel(run_it)
        elif run_module:
            # handle the "-m" command
            def run_it():
                import runpy
                runpy.run_module(sys.argv[0], None, '__main__', True)
            success = run_toplevel(run_it)
        elif run_stdin:
            # handle the case where no command/filename/module is specified
            # on the command-line.
            if go_interactive or sys.stdin.isatty():
                # If stdin is a tty or if "-i" is specified, we print
                # a banner and run $PYTHONSTARTUP.
                print_banner()
                python_startup = os.getenv('PYTHONSTARTUP')
                if python_startup:
                    try:
                        startup = open(python_startup).read()
                    except IOError:
                        pass
                    else:
                        def run_it():
                            co_python_startup = compile(startup,
                                                        python_startup,
                                                        'exec')
                            exec co_python_startup in mainmodule.__dict__
                        run_toplevel(run_it)
                # Then we need a prompt.
                go_interactive = True
            else:
                # If not interactive, just read and execute stdin normally.
                def run_it():
                    co_stdin = compile(sys.stdin.read(), '<stdin>', 'exec')
                    exec co_stdin in mainmodule.__dict__
                mainmodule.__file__ = '<stdin>'
                success = run_toplevel(run_it)
        else:
            # handle the common case where a filename is specified
            # on the command-line.
            mainmodule.__file__ = sys.argv[0]
            scriptdir = resolvedirof(sys.argv[0])
            sys.path.insert(0, scriptdir)
            success = run_toplevel(execfile, sys.argv[0], mainmodule.__dict__)

        # start a prompt if requested
        if inspect_requested():
            from _pypy_interact import interactive_console
            success = run_toplevel(interactive_console, mainmodule)
    except SystemExit, e:
        return e.code
    else:
        return not success

def resolvedirof(filename):
    try:
        filename = os.path.abspath(filename)
    except OSError:
        pass
    dirname = os.path.dirname(filename)
    if os.path.islink(filename):
        try:
            link = os.readlink(filename)
        except OSError:
            pass
        else:
            return resolvedirof(os.path.join(dirname, link))
    return dirname

def print_banner():
    print 'Python %s on %s' % (sys.version, sys.platform)
    print ('Type "help", "copyright", "credits" or '
           '"license" for more information.')

def entry_point(executable, argv, nanos):
    executable = setup_initial_paths(executable, nanos)
    try:
        cmdline = parse_command_line(argv)
    except CommandLineError, e:
        print_error(str(e))
        return 2
    if cmdline is None:
        return 0
    else:
        return run_command_line(**cmdline)


if __name__ == '__main__':
    import autopath
    import nanos
    # obscure! try removing the following line, see how it crashes, and
    # guess why...
    ImStillAroundDontForgetMe = sys.modules['__main__']
    sys.ps1 = '>>>> '
    sys.ps2 = '.... '

    # debugging only
    def pypy_initial_path(s):
        from pypy.module.sys.state import getinitialpath
        try:
            return getinitialpath(s)
        except OSError:
            return None

    # stick the current sys.path into $PYTHONPATH, so that CPython still
    # finds its own extension modules :-/
    import os
    os.environ['PYTHONPATH'] = ':'.join(sys.path)

    from pypy.module.sys.version import PYPY_VERSION
    sys.pypy_version_info = PYPY_VERSION
    sys.pypy_initial_path = pypy_initial_path
    os = nanos.os_module_for_testing
    sys.exit(entry_point(sys.argv[0], sys.argv[1:], os))
    #sys.exit(entry_point('app_main.py', sys.argv[1:]))
