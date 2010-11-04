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

def handle_sys_exit(e):
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
        handle_sys_exit(e)
    except:
        display_exception()
        return False
    return True   # success

def display_exception():
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
        return # done

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

def get_library_path(executable):
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
            search = dirname    # walk to the parent directory
            continue
        break      # found!
    return newpath

def setup_initial_paths(executable, nanos):
    # a substituted os if we are translated
    global os
    os = nanos
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

    newpath = get_library_path(executable)
    path = os.getenv('PYTHONPATH')
    if path:
        newpath = path.split(os.pathsep) + newpath
    # remove duplicates
    _seen = {}
    del sys.path[:]
    for dir in newpath:
        if dir not in _seen:
            sys.path.append(dir)
            _seen[dir] = True
    return executable

# Order is significant!
sys_flags = (
    "debug",
    "py3k_warning",
    "division_warning",
    "division_new",
    "inspect",
    "interactive",
    "optimize",
    "dont_write_bytecode",
    "no_user_site",
    "no_site",
    "ignore_environment",
    "tabcheck",
    "verbose",
    "unicode",
    "bytes_warning",
)


default_options = dict.fromkeys(
    sys_flags +
    ("run_command",
    "run_module",
    "run_stdin",
    "warnoptions",
    "unbuffered"), False)


def parse_command_line(argv):
    options = default_options.copy()
    options['warnoptions'] = []
    print_sys_flags = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if not arg.startswith('-'):
            break
        if arg == '-i':
            options["inspect"] = options["interactive"] = True
        elif arg == '-d':
            options["debug"] = True
        elif arg == '-3':
            options["py3k_warning"] = True
        elif arg == '-E':
            options["ignore_environment"] = True
        elif arg == '-U':
            options["unicode"] = True
        elif arg.startswith('-b'):
            options["bytes_warning"] = arg.count('b')
        elif arg.startswith('-t'):
            options["tabcheck"] = arg.count('t')
        elif arg.startswith('-v'):
            options["verbose"] += arg.count('v')
        elif arg.startswith('-Q'):
            div, i = get_argument("-Q", argv, i)
            if div == "warn":
                options["division_warning"] = 1
            elif div == "warnall":
                options["division_warning"] = 2
            elif div == "new":
                options["division_new"] = True
            elif div != "old":
                raise CommandLineError("invalid division option: %r" % (div,))
        elif arg.startswith('-O'):
            options["optimize"] = arg.count('O')
        elif arg == '-B':
            options["dont_write_bytecode"] = True
        elif arg.startswith('-c'):
            options["cmd"], i = get_argument('-c', argv, i)
            argv[i] = '-c'
            options["run_command"] = True
            break
        elif arg == '-u':
            options["unbuffered"] = True
        elif arg == '-O' or arg == '-OO':
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
        elif arg == '-s':
            options["no_user_site"] = True
        elif arg == '-S':
            options["no_site"] = True
        elif arg == '-':
            options["run_stdin"] = True
            break     # not an option but a file name representing stdin
        elif arg.startswith('-m'):
            module, i = get_argument('-m', argv, i)
            argv[i] = module
            options["run_module"] = True
            break
        elif arg.startswith('-W'):
            warnoption, i = get_argument('-W', argv, i)
            options["warnoptions"].append(warnoption)
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
        # for testing
        elif not we_are_translated() and arg == "--print-sys-flags":
            print_sys_flags = True
        else:
            raise CommandLineError('unrecognized option %r' % (arg,))
        i += 1
    sys.argv[:] = argv[i:]    # don't change the list that sys.argv is bound to
    if not sys.argv:          # (relevant in case of "reload(sys)")
        sys.argv.append('')
        options["run_stdin"] = True
    if print_sys_flags:
        flag_opts = ["%s=%s" % (opt, int(value))
                     for opt, value in options.iteritems()
                     if isinstance(value, int)]
        "(%s)" % (", ".join(flag_opts),)
        print flag_opts
    if we_are_translated():
        flags = [options[flag] for flag in sys_flags]
        sys.flags = type(sys.flags)(flags)
        sys.py3kwarning = sys.flags.py3k_warning
    return options

def run_command_line(interactive,
                     run_command,
                     no_site,
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

    if not no_site:
        try:
            import site
        except:
            print >> sys.stderr, "'import site' failed"

    # update sys.path *after* loading site.py, in case there is a
    # "site.py" file in the script's directory.
    sys.path.insert(0, '')

    pythonwarnings = os.getenv('PYTHONWARNINGS')
    if pythonwarnings:
        warnoptions.extend(pythonwarnings.split(','))
    if warnoptions:
        sys.warnoptions[:] = warnoptions
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
        #     * insepct=True, either from the "-i" option or from the fact that
        #     we printed the banner;
        # or
        #     * PYTHONINSPECT is set and stdin is a tty.
        #
        return (interactive or
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
            if interactive or sys.stdin.isatty():
                # If stdin is a tty or if "-i" is specified, we print
                # a banner and run $PYTHONSTARTUP.
                print_banner()
                python_startup = os.getenv('PYTHONSTARTUP')
                if python_startup:
                    try:
                        f = open(python_startup)
                        startup = f.read()
                        f.close()
                    except IOError, e:
                        print >> sys.stderr, "Could not open PYTHONSTARTUP"
                        print >> sys.stderr, "IOError:", e
                    else:
                        def run_it():
                            co_python_startup = compile(startup,
                                                        python_startup,
                                                        'exec')
                            exec co_python_startup in mainmodule.__dict__
                        run_toplevel(run_it)
                # Then we need a prompt.
                interactive = True
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

    except SystemExit, e:
        status = e.code
        if inspect_requested():
            display_exception()
    else:
        status = not success

    # start a prompt if requested
    if inspect_requested():
        inteactive = False
        try:
            from _pypy_interact import interactive_console
            success = run_toplevel(interactive_console, mainmodule)
        except SystemExit, e:
            status = e.code
        else:
            status = not success

    return status

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
    reset = []
    if 'PYTHONINSPECT_' in os.environ:
        reset.append(('PYTHONINSPECT', os.environ.get('PYTHONINSPECT', '')))
        os.environ['PYTHONINSPECT'] = os.environ['PYTHONINSPECT_']

    # no one should change to which lists sys.argv and sys.path are bound
    old_argv = sys.argv
    old_path = sys.path

    from pypy.module.sys.version import PYPY_VERSION
    sys.pypy_version_info = PYPY_VERSION
    sys.pypy_initial_path = pypy_initial_path
    os = nanos.os_module_for_testing
    sys.ps1 = '>>>> '
    sys.ps2 = '.... '
    try:
        sys.exit(int(entry_point(sys.argv[0], sys.argv[1:], os)))
    finally:
        sys.ps1 = '>>> '     # restore the normal ones, in case
        sys.ps2 = '... '     # we are dropping to CPython's prompt
        import os; os.environ.update(reset)
        assert old_argv is sys.argv
        assert old_path is sys.path
