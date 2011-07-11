#! /usr/bin/env python
# App-level version of py.py.
# See test/test_app_main.
"""
options:
  -i             inspect interactively after running script
  -O             dummy optimization flag for compatibility with C Python
  -c cmd         program passed in as CMD (terminates option list)
  -S             do not 'import site' on initialization
  -u             unbuffered binary stdout and stderr
  -h, --help     show this help message and exit
  -m mod         library module to be run as a script (terminates option list)
  -W arg         warning control (arg is action:message:category:module:lineno)
  -E             ignore environment variables (such as PYTHONPATH)
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
                stderr.write(exitcode)
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

def print_info(*args):
    try:
        options = sys.pypy_translation_info
    except AttributeError:
        print >> sys.stderr, 'no translation information found'
    else:
        optitems = options.items()
        optitems.sort()
        for name, value in optitems:
            print ' %51s: %s' % (name, value)
    raise SystemExit

def print_help(*args):
    print 'usage: %s [options] [-c cmd|-m mod|file.py|-] [arg...]' % (
        sys.executable,)
    print __doc__.rstrip()
    if 'pypyjit' in sys.builtin_module_names:
        _print_jit_help()
    print
    raise SystemExit

def _print_jit_help():
    import pypyjit
    items = pypyjit.defaults.items()
    items.sort()
    for key, value in items:
        print '  --jit %s=N %slow-level JIT parameter (default %s)' % (
            key, ' '*(18-len(key)), value)
    print '  --jit off                  turn off the JIT'

def print_version(*args):
    print "Python", sys.version
    raise SystemExit

def set_jit_option(options, jitparam, *args):
    if 'pypyjit' not in sys.builtin_module_names:
        print >> sys.stderr, ("Warning: No jit support in %s" %
                              (sys.executable,))
    else:
        import pypyjit
        pypyjit.set_param(jitparam)

class CommandLineError(Exception):
    pass

def print_error(msg):
    print >> sys.stderr, msg
    print >> sys.stderr, 'usage: %s [options]' % (sys.executable,)
    print >> sys.stderr, 'Try `%s -h` for more information.' % (sys.executable,)

def fdopen(fd, mode, bufsize=-1):
    try:
        fdopen = file.fdopen
    except AttributeError:     # only on top of CPython, running tests
        from os import fdopen
    return fdopen(fd, mode, bufsize)

def set_unbuffered_io():
    sys.stdin  = sys.__stdin__  = fdopen(0, 'rb', 0)
    sys.stdout = sys.__stdout__ = fdopen(1, 'wb', 0)
    sys.stderr = sys.__stderr__ = fdopen(2, 'wb', 0)

def set_fully_buffered_io():
    sys.stdout = sys.__stdout__ = fdopen(1, 'w')

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

def get_library_path(executable):
    search = executable
    while 1:
        dirname = resolvedirof(search)
        if dirname == search:
            # not found!  let's hope that the compiled-in path is ok
            print >> sys.stderr, """\
debug: WARNING: Library path not found, using compiled-in sys.path.
debug: WARNING: 'sys.prefix' will not be set.
debug: WARNING: Make sure the pypy binary is kept inside its tree of files.
debug: WARNING: It is ok to create a symlink to it from somewhere else."""
            newpath = sys.path[:]
            break
        newpath = sys.pypy_initial_path(dirname)
        if newpath is None:
            search = dirname    # walk to the parent directory
            continue
        break      # found!
    return newpath

def setup_sys_executable(executable, nanos):
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
    #
    # 'sys.executable' should not end up being an non-existing file;
    # just use '' in this case. (CPython issue #7774)
    if not os.path.isfile(sys.executable):
        sys.executable = ''

def setup_initial_paths(ignore_environment=False, **extra):
    newpath = get_library_path(sys.executable)
    readenv = not ignore_environment
    path = readenv and os.getenv('PYTHONPATH')
    if path:
        newpath = path.split(os.pathsep) + newpath
    # remove duplicates
    _seen = {}
    del sys.path[:]
    for dir in newpath:
        if dir not in _seen:
            sys.path.append(dir)
            _seen[dir] = True

def set_io_encoding(io_encoding):
    try:
        import _file
    except ImportError:
        import ctypes # HACK: while running on top of CPython
        set_file_encoding = ctypes.pythonapi.PyFile_SetEncodingAndErrors
        set_file_encoding.argtypes = [ctypes.py_object, ctypes.c_char_p, ctypes.c_char_p]
    else:
        set_file_encoding = _file.set_file_encoding
    if ":" in io_encoding:
        encoding, errors = io_encoding.split(":", 1)
    else:
        encoding, errors = io_encoding, None
    for f in [sys.stdin, sys.stdout, sys.stderr]:
        set_file_encoding(f, encoding, errors)

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
    "unbuffered"), 0)


PYTHON26 = True

def simple_option(options, name, iterargv):
    options[name] += 1

def div_option(options, div, iterargv):
    if div == "warn":
        options["division_warning"] = 1
    elif div == "warnall":
        options["division_warning"] = 2
    elif div == "new":
        options["division_new"] = 1
    elif div != "old":
        raise CommandLineError("invalid division option: %r" % (div,))

def c_option(options, runcmd, iterargv):
    options["run_command"] = runcmd
    return ['-c'] + list(iterargv)

def m_option(options, runmodule, iterargv):
    options["run_module"] = True
    return [runmodule] + list(iterargv)

def W_option(options, warnoption, iterargv):
    options["warnoptions"].append(warnoption)

def end_options(options, _, iterargv):
    return list(iterargv)

cmdline_options = {
    # simple options just increment the counter of the options listed above
    'd': (simple_option, 'debug'),
    'i': (simple_option, 'interactive'),
    'O': (simple_option, 'optimize'),
    'S': (simple_option, 'no_site'),
    'E': (simple_option, 'ignore_environment'),
    't': (simple_option, 'tabcheck'),
    'v': (simple_option, 'verbose'),
    'U': (simple_option, 'unicode'),
    'u': (simple_option, 'unbuffered'),
    # more complex options
    'Q':         (div_option,      Ellipsis),
    'c':         (c_option,        Ellipsis),
    'm':         (m_option,        Ellipsis),
    'W':         (W_option,        Ellipsis),
    'V':         (print_version,   None),
    '--version': (print_version,   None),
    '--info':    (print_info,      None),
    'h':         (print_help,      None),
    '--help':    (print_help,      None),
    '--jit':     (set_jit_option,  Ellipsis),
    '--':        (end_options,     None),
    }

if PYTHON26:
    cmdline_options.update({
        '3': (simple_option, 'py3k_warning'),
        'B': (simple_option, 'dont_write_bytecode'),
        's': (simple_option, 'no_user_site'),
        'b': (simple_option, 'bytes_warning'),
        })


def handle_argument(c, options, iterargv, iterarg=iter(())):
    function, funcarg = cmdline_options[c]
    #
    # If needed, fill in the real argument by taking it from the command line
    if funcarg is Ellipsis:
        remaining = list(iterarg)
        if remaining:
            funcarg = ''.join(remaining)
        else:
            try:
                funcarg = iterargv.next()
            except StopIteration:
                if len(c) == 1:
                    c = '-' + c
                raise CommandLineError('Argument expected for the %r option' % c)
    #
    return function(options, funcarg, iterargv)


def parse_command_line(argv):
    options = default_options.copy()
    options['warnoptions'] = []
    #
    iterargv = iter(argv)
    argv = None
    for arg in iterargv:
        #
        # If the next argument isn't at least two characters long or
        # doesn't start with '-', stop processing
        if len(arg) < 2 or arg[0] != '-':
            if IS_WINDOWS and arg == '/?':      # special case
                print_help()
            argv = [arg] + list(iterargv)    # finishes processing
        #
        # If the next argument is directly in cmdline_options, handle
        # it as a single argument
        elif arg in cmdline_options:
            argv = handle_argument(arg, options, iterargv)
        #
        # Else interpret the rest of the argument character by character
        else:
            iterarg = iter(arg)
            iterarg.next()     # skip the '-'
            for c in iterarg:
                if c not in cmdline_options:
                    raise CommandLineError('Unknown option: -%s' % (c,))
                argv = handle_argument(c, options, iterargv, iterarg)

    if not argv:
        argv = ['']
        options["run_stdin"] = True
    elif argv[0] == '-':
        options["run_stdin"] = True

    # don't change the list that sys.argv is bound to
    # (relevant in case of "reload(sys)")
    sys.argv[:] = argv

    if (PYTHON26 and not options["ignore_environment"] and os.getenv('PYTHONNOUSERSITE')):
        options["no_user_site"] = True

    if (options["interactive"] or
        (not options["ignore_environment"] and os.getenv('PYTHONINSPECT'))):
        options["inspect"] = True

    if PYTHON26 and we_are_translated():
        flags = [options[flag] for flag in sys_flags]
        sys.flags = type(sys.flags)(flags)
        sys.py3kwarning = sys.flags.py3k_warning

        if sys.py3kwarning:
            print >> sys.stderr, (
                "Warning: pypy does not implement py3k warnings")

##    if not we_are_translated():
##        for key in sorted(options):
##            print '%40s: %s' % (key, options[key])
##        print '%40s: %s' % ("sys.argv", sys.argv)

    return options

def run_command_line(interactive,
                     inspect,
                     run_command,
                     no_site,
                     run_module,
                     run_stdin,
                     warnoptions,
                     unbuffered,
                     ignore_environment,
                     **ignored):
    # with PyPy in top of CPython we can only have around 100 
    # but we need more in the translated PyPy for the compiler package
    if '__pypy__' not in sys.builtin_module_names:
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

    readenv = not ignore_environment
    io_encoding = readenv and os.getenv("PYTHONIOENCODING")
    if io_encoding:
        set_io_encoding(io_encoding)

    pythonwarnings = readenv and os.getenv('PYTHONWARNINGS')
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
        # We get an interactive prompt in one of the following three cases:
        #
        #     * interactive=True, from the "-i" option
        # or
        #     * inspect=True and stdin is a tty
        # or
        #     * PYTHONINSPECT is set and stdin is a tty.
        #
        return (interactive or
                ((inspect or (readenv and os.getenv('PYTHONINSPECT')))
                 and sys.stdin.isatty()))

    success = True

    try:
        if run_command != 0:
            # handle the "-c" command
            # Put '' on sys.path
            sys.path.insert(0, '')

            def run_it():
                exec run_command in mainmodule.__dict__
            success = run_toplevel(run_it)
        elif run_module:
            # handle the "-m" command
            # '' on sys.path is required also here
            sys.path.insert(0, '')
            import runpy
            success = run_toplevel(runpy._run_module_as_main, sys.argv[0])
        elif run_stdin:
            # handle the case where no command/filename/module is specified
            # on the command-line.

            # update sys.path *after* loading site.py, in case there is a
            # "site.py" file in the script's directory. Only run this if we're
            # executing the interactive prompt, if we're running a script we
            # put it's directory on sys.path
            sys.path.insert(0, '')

            if interactive or sys.stdin.isatty():
                # If stdin is a tty or if "-i" is specified, we print
                # a banner and run $PYTHONSTARTUP.
                print_banner()
                python_startup = readenv and os.getenv('PYTHONSTARTUP')
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
                inspect = True
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
            filename = sys.argv[0]
            mainmodule.__file__ = filename
            sys.path.insert(0, resolvedirof(filename))
            # assume it's a pyc file only if its name says so.
            # CPython goes to great lengths to detect other cases
            # of pyc file format, but I think it's ok not to care.
            import imp
            if IS_WINDOWS:
                filename = filename.lower()
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                args = (imp._run_compiled_module, '__main__',
                        sys.argv[0], None, mainmodule)
            else:
                # maybe it's the name of a directory or a zip file
                filename = sys.argv[0]
                importer = imp._getimporter(filename)
                if not isinstance(importer, imp.NullImporter):
                    # yes.  put the filename in sys.path[0] and import
                    # the module __main__
                    import runpy
                    sys.path.insert(0, filename)
                    args = (runpy._run_module_as_main, '__main__', False)
                else:
                    # no.  That's the normal path, "pypy stuff.py".
                    args = (execfile, filename, mainmodule.__dict__)
            success = run_toplevel(*args)

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
    setup_sys_executable(executable, nanos)
    try:
        cmdline = parse_command_line(argv)
    except CommandLineError, e:
        print_error(str(e))
        return 2
    except SystemExit, e:
        return e.code or 0
    setup_initial_paths(**cmdline)
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

    # add an emulator for these pypy-only or 2.7-only functions
    # (for test_pyc_commandline_argument)
    import imp, runpy
    def _run_compiled_module(modulename, filename, file, module):
        import os
        assert modulename == '__main__'
        assert os.path.isfile(filename)
        assert filename.endswith('.pyc')
        assert file is None
        assert module.__name__ == '__main__'
        print 'in _run_compiled_module'
    def _getimporter(path):
        import os, imp
        if os.path.isdir(path):
            return None
        else:
            return imp.NullImporter(path)

    imp._run_compiled_module = _run_compiled_module
    imp._getimporter = _getimporter

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
    try:
        sys.exit(int(entry_point(sys.argv[0], sys.argv[1:], os)))
    finally:
        # restore the normal prompt (which was changed by _pypy_interact), in
        # case we are dropping to CPython's prompt
        sys.ps1 = '>>> '
        sys.ps2 = '... '
        import os; os.environ.update(reset)
        assert old_argv is sys.argv
        assert old_path is sys.path
