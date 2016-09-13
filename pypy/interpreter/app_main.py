#! /usr/bin/env python
# This is pure Python code that handles the main entry point into "pypy".
# See test/test_app_main.

# Missing vs CPython: -b, -d, -x
from __future__ import print_function, unicode_literals
USAGE1 = __doc__ = """\
Options and arguments (and corresponding environment variables):
-B     : don't write .py[co] files on import; also PYTHONDONTWRITEBYTECODE=x
-c cmd : program passed in as string (terminates option list)
-E     : ignore PYTHON* environment variables (such as PYTHONPATH)
-h     : print this help message and exit (also --help)
-i     : inspect interactively after running script; forces a prompt even
         if stdin does not appear to be a terminal; also PYTHONINSPECT=x
-I     : isolate Python from the user's environment (implies -E and -s)
-m mod : run library module as a script (terminates option list)
-O     : skip assert statements; also PYTHONOPTIMIZE=x
-OO    : remove docstrings when importing modules in addition to -O
-q     : don't print version and copyright messages on interactive startup
-s     : don't add user site directory to sys.path; also PYTHONNOUSERSITE
-S     : don't imply 'import site' on initialization
-u     : unbuffered binary stdout and stderr, stdin always buffered;
         also PYTHONUNBUFFERED=x
-v     : verbose (trace import statements); also PYTHONVERBOSE=x
         can be supplied multiple times to increase verbosity
-V     : print the Python version number and exit (also --version)
-W arg : warning control; arg is action:message:category:module:lineno
         also PYTHONWARNINGS=arg
-X opt : set implementation-specific option
file   : program read from script file
-      : program read from stdin (default; interactive mode if a tty)
arg ...: arguments passed to program in sys.argv[1:]
PyPy options and arguments:
--info : print translation information about this PyPy executable
"""
# Missing vs CPython: PYTHONHOME
USAGE2 = """
Other environment variables:
PYTHONSTARTUP: file executed on interactive startup (no default)
PYTHONPATH   : %r-separated list of directories prefixed to the
               default module search path.  The result is sys.path.
PYTHONCASEOK : ignore case in 'import' statements (Windows).
PYTHONIOENCODING: Encoding[:errors] used for stdin/stdout/stderr.
PYPY_IRC_TOPIC: if set to a non-empty value, print a random #pypy IRC
               topic at startup of interactive mode.
PYPYLOG: If set to a non-empty value, enable logging.
"""

try:
    from __pypy__ import hidden_applevel, StdErrPrinter
except ImportError:
    hidden_applevel = lambda f: f
    StdErrPrinter = None
try:
    from _ast import PyCF_ACCEPT_NULL_BYTES
except ImportError:
    PyCF_ACCEPT_NULL_BYTES = 0
import errno
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
                print(exitcode, file=sys.stderr)
            except:
                pass   # too bad
            exitcode = 1
    raise SystemExit(exitcode)

@hidden_applevel
def run_toplevel(f, *fargs, **fkwds):
    """Calls f() and handles all OperationErrors.
    Intended use is to run the main program or one interactive statement.
    run_protected() handles details like forwarding exceptions to
    sys.excepthook(), catching SystemExit, etc.
    """
    try:
        # run it
        try:
            f(*fargs, **fkwds)
        finally:
            sys.settrace(None)
            sys.setprofile(None)
    except SystemExit as e:
        handle_sys_exit(e)
    except BaseException as e:
        display_exception(e)
        return False
    return True   # success

def display_exception(e):
    etype, evalue, etraceback = type(e), e, e.__traceback__
    try:
        # extra debugging info in case the code below goes very wrong
        if DEBUG and hasattr(sys, 'stderr'):
            s = getattr(etype, '__name__', repr(etype))
            print("debug: exception-type: ", s, file=sys.stderr)
            print("debug: exception-value:", str(evalue), file=sys.stderr)
            tbentry = etraceback
            if tbentry:
                while tbentry.tb_next:
                    tbentry = tbentry.tb_next
                lineno = tbentry.tb_lineno
                filename = tbentry.tb_frame.f_code.co_filename
                print("debug: exception-tb:    %s:%d" % (filename, lineno),
                      file=sys.stderr)

        # set the sys.last_xxx attributes
        sys.last_type = etype
        sys.last_value = evalue
        sys.last_traceback = etraceback

        # call sys.excepthook
        hook = getattr(sys, 'excepthook', originalexcepthook)
        hook(etype, evalue, etraceback)
        return # done

    except BaseException as e:
        try:
            initstdio()
            stderr = sys.stderr
            print('Error calling sys.excepthook:', file=stderr)
            originalexcepthook(type(e), e, e.__traceback__)
            print(file=stderr)
            print('Original exception was:', file=stderr)
        except:
            pass   # too bad

    # we only get here if sys.excepthook didn't do its job
    originalexcepthook(etype, evalue, etraceback)


# ____________________________________________________________
# Option parsing

def print_info(*args):
    initstdio()
    try:
        options = sys.pypy_translation_info
    except AttributeError:
        print('no translation information found', file=sys.stderr)
    else:
        optitems = sorted(options.items())
        current = []
        for key, value in optitems:
            group = key.split('.')
            name = group.pop()
            n = 0
            while n < min(len(current), len(group)) and current[n] == group[n]:
                n += 1
            while n < len(group):
                print('%s[%s]' % ('    ' * n, group[n]))
                n += 1
            print('%s%s = %r' % ('    ' * n, name, value))
            current = group
    raise SystemExit

def get_sys_executable():
    return getattr(sys, 'executable', 'pypy')

def print_help(*args):
    import os
    initstdio()
    print('usage: %s [option] ... [-c cmd | -m mod | file | -] [arg] ...' % (
        get_sys_executable(),))
    print(USAGE1, end='')
    if 'pypyjit' in sys.builtin_module_names:
        print("--jit options: advanced JIT options: try 'off' or 'help'")
    print(USAGE2 % (os.pathsep,), end='')
    raise SystemExit

def _print_jit_help():
    initstdio()
    try:
        import pypyjit
    except ImportError:
        print("No jit support in %s" % (get_sys_executable(),), file=sys.stderr)
        return
    items = sorted(pypyjit.defaults.items())
    print('Advanced JIT options: a comma-separated list of OPTION=VALUE:')
    for key, value in items:
        print()
        print(' %s=N' % (key,))
        doc = '%s (default %s)' % (pypyjit.PARAMETER_DOCS[key], value)
        while len(doc) > 72:
            i = doc[:74].rfind(' ')
            if i < 0:
                i = doc.find(' ')
                if i < 0:
                    i = len(doc)
            print('    ' + doc[:i])
            doc = doc[i+1:]
        print('    ' + doc)
    print()
    print(' off')
    print('    turn off the JIT')
    print(' help')
    print('    print this page')

def print_version(*args):
    initstdio()
    print ("Python", sys.version, file=sys.stderr)
    raise SystemExit


def funroll_loops(*args):
    print("Vroom vroom, I'm a racecar!")


def set_jit_option(options, jitparam, *args):
    if jitparam == 'help':
        _print_jit_help()
        raise SystemExit
    if 'pypyjit' not in sys.builtin_module_names:
        initstdio()
        print("Warning: No jit support in %s" % (get_sys_executable(),),
              file=sys.stderr)
    else:
        import pypyjit
        pypyjit.set_param(jitparam)

class CommandLineError(Exception):
    pass

def print_error(msg):
    print(msg, file=sys.stderr)
    print('usage: %s [options]' % (get_sys_executable(),), file=sys.stderr)
    print('Try `%s -h` for more information.' % (get_sys_executable(),), file=sys.stderr)

def fdopen(fd, mode, bufsize=-1):
    try:
        fdopen = file.fdopen
    except AttributeError:     # only on top of CPython, running tests
        from os import fdopen
    return fdopen(fd, mode, bufsize)

# ____________________________________________________________
# Main entry point

def we_are_translated():
    # app-level, very different from rpython.rlib.objectmodel.we_are_translated
    return hasattr(sys, 'pypy_translation_info')

IS_WINDOWS = 'nt' in sys.builtin_module_names

def setup_and_fix_paths(ignore_environment=False, **extra):
    import os
    newpath = sys.path[:]
    del sys.path[:]
    # first prepend PYTHONPATH
    readenv = not ignore_environment
    path = readenv and os.getenv('PYTHONPATH')
    if path:
        sys.path.extend(path.split(os.pathsep))
    # then add again the original entries, ignoring duplicates
    _seen = set()
    for dir in newpath:
        if dir not in _seen:
            sys.path.append(dir)
            _seen.add(dir)

def initstdio(encoding=None, unbuffered=False):
    if hasattr(sys, 'stdin'):
        return # already initialized

    if StdErrPrinter is not None:
        sys.stderr = sys.__stderr__ = StdErrPrinter(2)

    # Hack to avoid recursion issues during bootstrapping: pre-import
    # the utf-8 and latin-1 codecs
    encerr = None
    try:
        import encodings.utf_8
        import encodings.latin_1
    except ImportError as e:
        encerr = e

    try:
        if encoding and ':' in encoding:
            encoding, errors = encoding.split(':', 1)
        else:
            errors = None

        sys.stderr = sys.__stderr__ = create_stdio(
            2, True, "<stderr>", encoding, 'backslashreplace', unbuffered)
        sys.stdout = sys.__stdout__ = create_stdio(
            1, True, "<stdout>", encoding, errors, unbuffered)

        try:
            sys.stdin = sys.__stdin__ = create_stdio(
                0, False, "<stdin>", encoding, errors, unbuffered)
        except IsADirectoryError:
            import os
            print("Python error: <stdin> is a directory, cannot continue",
                  file=sys.stderr)
            os._exit(1)
    finally:
        if encerr:
            display_exception(encerr)
            del encerr

def create_stdio(fd, writing, name, encoding, errors, unbuffered):
    import io
    # stdin is always opened in buffered mode, first because it
    # shouldn't make a difference in common use cases, second because
    # TextIOWrapper depends on the presence of a read1() method which
    # only exists on buffered streams.
    buffering = 0 if unbuffered and writing else -1
    mode = 'w' if writing else 'r'
    try:
        buf = io.open(fd, mode + 'b', buffering, closefd=False)
    except OSError as e:
        if e.errno != errno.EBADF:
            raise
        return None

    raw = buf.raw if buffering else buf
    raw.name = name
    # translate \r\n to \n for sys.stdin on Windows
    newline = None if sys.platform == 'win32' and not writing else '\n'
    stream = io.TextIOWrapper(buf, encoding, errors, newline=newline,
                              line_buffering=unbuffered or raw.isatty())
    stream.mode = mode
    return stream


# Order is significant!
sys_flags = (
    "debug",
    "inspect",
    "interactive",
    "optimize",
    "dont_write_bytecode",
    "no_user_site",
    "no_site",
    "ignore_environment",
    "verbose",
    "bytes_warning",
    "quiet",
    "hash_randomization",
    "isolated",
)

default_options = dict.fromkeys(
    sys_flags +
    ("run_command",
    "run_module",
    "run_stdin",
    "warnoptions",
    "unbuffered"), 0)

def simple_option(options, name, iterargv):
    options[name] += 1

def isolated_option(options, name, iterargv):
    options[name] += 1
    options["no_user_site"] += 1
    options["ignore_environment"] += 1

def c_option(options, runcmd, iterargv):
    options["run_command"] = runcmd
    return ['-c'] + list(iterargv)

def m_option(options, runmodule, iterargv):
    options["run_module"] = runmodule
    return ['-m'] + list(iterargv)

def X_option(options, xoption, iterargv):
    options["_xoptions"].append(xoption)

def W_option(options, warnoption, iterargv):
    options["warnoptions"].append(warnoption)

def end_options(options, _, iterargv):
    return list(iterargv)

def ignore_option(*args):
    pass

cmdline_options = {
    # simple options just increment the counter of the options listed above
    'b': (simple_option, 'bytes_warning'),
    'B': (simple_option, 'dont_write_bytecode'),
    'd': (simple_option, 'debug'),
    'E': (simple_option, 'ignore_environment'),
    'I': (isolated_option, 'isolated'),
    'i': (simple_option, 'interactive'),
    'O': (simple_option, 'optimize'),
    's': (simple_option, 'no_user_site'),
    'S': (simple_option, 'no_site'),
    'u': (simple_option, 'unbuffered'),
    'v': (simple_option, 'verbose'),
    'q': (simple_option, 'quiet'),
    # more complex options
    'c':         (c_option,        Ellipsis),
    '?':         (print_help,      None),
    'h':         (print_help,      None),
    '--help':    (print_help,      None),
    'm':         (m_option,        Ellipsis),
    'W':         (W_option,        Ellipsis),
    'X':         (X_option,        Ellipsis),
    'V':         (print_version,   None),
    '--version': (print_version,   None),
    '--info':    (print_info,      None),
    '--jit':     (set_jit_option,  Ellipsis),
    '-funroll-loops': (funroll_loops, None),
    '--':        (end_options,     None),
    'R':         (ignore_option,   None),      # previously hash_randomization
    }

def handle_argument(c, options, iterargv, iterarg=iter(())):
    function, funcarg = cmdline_options[c]

    # If needed, fill in the real argument by taking it from the command line
    if funcarg is Ellipsis:
        remaining = list(iterarg)
        if remaining:
            funcarg = ''.join(remaining)
        else:
            try:
                funcarg = next(iterargv)
            except StopIteration:
                if len(c) == 1:
                    c = '-' + c
                raise CommandLineError('Argument expected for the %r option' % c)

    return function(options, funcarg, iterargv)

def parse_env(name, key, options):
    ''' Modify options inplace if name exists in os.environ
    '''
    import os
    v = os.getenv(name)
    if v:
        options[key] = max(1, options[key])
        try:
            newval = int(v)
        except ValueError:
            pass
        else:
            newval = max(1, newval)
            options[key] = max(options[key], newval)

def parse_command_line(argv):
    import os
    options = default_options.copy()
    options['warnoptions'] = []
    options['_xoptions'] = []

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
            next(iterarg)      # skip the '-'
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

    if not options["ignore_environment"]:
        parse_env('PYTHONDEBUG', "debug", options)
        if os.getenv('PYTHONDONTWRITEBYTECODE'):
            options["dont_write_bytecode"] = 1
        if os.getenv('PYTHONNOUSERSITE'):
            options["no_user_site"] = 1
        if os.getenv('PYTHONUNBUFFERED'):
            options["unbuffered"] = 1
        parse_env('PYTHONVERBOSE', "verbose", options)
        parse_env('PYTHONOPTIMIZE', "optimize", options)
    if (options["interactive"] or
        (not options["ignore_environment"] and os.getenv('PYTHONINSPECT'))):
        options["inspect"] = 1

##    We don't print the warning, because it offers no additional security
##    in CPython either (http://bugs.python.org/issue14621)
##    if (options["hash_randomization"] or os.getenv('PYTHONHASHSEED')):
##        print >> sys.stderr, (
##            "Warning: pypy does not implement hash randomization")

    if we_are_translated():
        flags = [options[flag] for flag in sys_flags]
        sys.flags = type(sys.flags)(flags)
        sys.dont_write_bytecode = bool(sys.flags.dont_write_bytecode)

        if sys.flags.optimize >= 1:
            import __pypy__
            __pypy__.set_debug(False)

    sys._xoptions = dict(x.split('=', 1) if '=' in x else (x, True)
                         for x in options['_xoptions'])

##    if not we_are_translated():
##        for key in sorted(options):
##            print '%40s: %s' % (key, options[key])
##        print '%40s: %s' % ("sys.argv", sys.argv)

    return options

# this indirection is needed to be able to import this module on python2, else
# we have a SyntaxError: unqualified exec in a nested function
@hidden_applevel
def exec_(src, dic):
    exec(src, dic)

@hidden_applevel
def run_command_line(interactive,
                     inspect,
                     run_command,
                     no_site,
                     run_module,
                     run_stdin,
                     warnoptions,
                     unbuffered,
                     ignore_environment,
                     quiet,
                     verbose,
                     **ignored):
    # with PyPy in top of CPython we can only have around 100
    # but we need more in the translated PyPy for the compiler package
    if '__pypy__' not in sys.builtin_module_names:
        sys.setrecursionlimit(5000)
    import os

    readenv = not ignore_environment
    io_encoding = os.getenv("PYTHONIOENCODING") if readenv else None
    initstdio(io_encoding, unbuffered)

    if we_are_translated():
        import __pypy__
        __pypy__.save_module_content_for_future_reload(sys)

    mainmodule = type(sys)('__main__')
    sys.modules['__main__'] = mainmodule

    if not no_site:
        try:
            import site
        except:
            print("'import site' failed", file=sys.stderr)

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
        try:
            # we need a version of getenv that bypasses Python caching
            from __pypy__.os import real_getenv
        except ImportError:
            # dont fail on CPython here
            real_getenv = os.getenv

        return (interactive or
                ((inspect or (readenv and real_getenv('PYTHONINSPECT')))
                 and sys.stdin.isatty()))

    success = True

    try:
        if run_command != 0:
            # handle the "-c" command
            # Put '' on sys.path
            try:
                bytes = run_command.encode()
            except BaseException as e:
                print("Unable to decode the command from the command line:",
                      file=sys.stderr)
                display_exception(e)
                success = False
            else:
                sys.path.insert(0, '')
                success = run_toplevel(exec_, bytes, mainmodule.__dict__)
        elif run_module != 0:
            # handle the "-m" command
            # '' on sys.path is required also here
            sys.path.insert(0, '')
            import runpy
            success = run_toplevel(runpy._run_module_as_main, run_module)
        elif run_stdin:
            # handle the case where no command/filename/module is specified
            # on the command-line.

            # update sys.path *after* loading site.py, in case there is a
            # "site.py" file in the script's directory. Only run this if we're
            # executing the interactive prompt, if we're running a script we
            # put it's directory on sys.path
            sys.path.insert(0, '')

            if interactive or sys.stdin.isatty():
                # If stdin is a tty or if "-i" is specified, we print a
                # banner (unless "-q" was specified) and run
                # $PYTHONSTARTUP.
                if not quiet:
                    print_banner(not no_site)
                python_startup = readenv and os.getenv('PYTHONSTARTUP')
                if python_startup:
                    try:
                        with open(python_startup, 'rb') as f:
                            startup = f.read()
                    except IOError as e:
                        print("Could not open PYTHONSTARTUP", file=sys.stderr)
                        print("IOError:", e, file=sys.stderr)
                    else:
                        @hidden_applevel
                        def run_it():
                            co_python_startup = compile(startup,
                                                        python_startup,
                                                        'exec',
                                                        PyCF_ACCEPT_NULL_BYTES)
                            exec_(co_python_startup, mainmodule.__dict__)
                        mainmodule.__file__ = python_startup
                        mainmodule.__cached__ = None
                        run_toplevel(run_it)
                        try:
                            del mainmodule.__file__
                        except (AttributeError, TypeError):
                            pass
                # Then we need a prompt.
                inspect = True
            else:
                # If not interactive, just read and execute stdin normally.
                if verbose:
                    print_banner(not no_site)
                @hidden_applevel
                def run_it():
                    co_stdin = compile(sys.stdin.read(), '<stdin>', 'exec',
                                       PyCF_ACCEPT_NULL_BYTES)
                    exec_(co_stdin, mainmodule.__dict__)
                mainmodule.__file__ = '<stdin>'
                mainmodule.__cached__ = None
                success = run_toplevel(run_it)
        else:
            # handle the common case where a filename is specified
            # on the command-line.
            filename = sys.argv[0]
            mainmodule.__file__ = filename
            mainmodule.__cached__ = None
            sys.path.insert(0, sys.pypy_resolvedirof(filename))
            # assume it's a pyc file only if its name says so.
            # CPython goes to great lengths to detect other cases
            # of pyc file format, but I think it's ok not to care.
            try:
                from _frozen_importlib import (
                    SourceFileLoader, SourcelessFileLoader)
            except ImportError:
                from _frozen_importlib_external import (
                    SourceFileLoader, SourcelessFileLoader)
            if IS_WINDOWS:
                filename = filename.lower()
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                loader = SourcelessFileLoader('__main__', filename)
                args = (loader.load_module, loader.name)
            else:
                filename = sys.argv[0]
                for hook in sys.path_hooks:
                    try:
                        importer = hook(filename)
                    except ImportError:
                        continue
                    # It's the name of a directory or a zip file.
                    # put the filename in sys.path[0] and import
                    # the module __main__
                    import runpy
                    sys.path.insert(0, filename)
                    args = (runpy._run_module_as_main, '__main__', False)
                    break
                else:
                    # That's the normal path, "pypy stuff.py".
                    # We don't actually load via SourceFileLoader
                    # because we require PyCF_ACCEPT_NULL_BYTES
                    loader = SourceFileLoader('__main__', filename)
                    mainmodule.__loader__ = loader
                    @hidden_applevel
                    def execfile(filename, namespace):
                        with open(filename, 'rb') as f:
                            code = f.read()
                        co = compile(code, filename, 'exec',
                                     PyCF_ACCEPT_NULL_BYTES)
                        exec_(co, namespace)
                    args = (execfile, filename, mainmodule.__dict__)
            success = run_toplevel(*args)

    except SystemExit as e:
        status = e.code
        if inspect_requested():
            display_exception(e)
    else:
        status = not success

    # start a prompt if requested
    if inspect_requested():
        try:
            from _pypy_interact import interactive_console
            pypy_version_info = getattr(sys, 'pypy_version_info', sys.version_info)
            irc_topic = pypy_version_info[3] != 'final' or (
                            readenv and os.getenv('PYPY_IRC_TOPIC'))
            success = run_toplevel(interactive_console, mainmodule,
                                   quiet=quiet or not irc_topic)
        except SystemExit as e:
            status = e.code
        else:
            status = not success

    return status

def print_banner(copyright):
    print('Python %s on %s' % (sys.version, sys.platform), file=sys.stderr)
    if copyright:
        print('Type "help", "copyright", "credits" or '
              '"license" for more information.', file=sys.stderr)

STDLIB_WARNING = """\
debug: WARNING: Library path not found, using compiled-in sys.path.
debug: WARNING: 'sys.prefix' will not be set.
debug: WARNING: Make sure the pypy binary is kept inside its tree of files.
debug: WARNING: It is ok to create a symlink to it from somewhere else."""

def setup_bootstrap_path(executable):
    """
    Try to do as little as possible and to have the stdlib in sys.path. In
    particular, we cannot use any unicode at this point, because lots of
    unicode operations require to be able to import encodings.
    """
    # at this point, sys.path is set to the compiled-in one, based on the
    # location where pypy was compiled. This is set during the objspace
    # initialization by module.sys.state.State.setinitialpath.
    #
    # Now, we try to find the absolute path of the executable and the stdlib
    # path
    executable = sys.pypy_find_executable(executable)
    stdlib_path = sys.pypy_find_stdlib(executable)
    if stdlib_path is None:
        initstdio()
        print(STDLIB_WARNING, file=sys.stderr)
    else:
        sys.path[:] = stdlib_path
    # from this point on, we are free to use all the unicode stuff we want,
    # This is important for py3k
    sys.executable = executable

@hidden_applevel
def entry_point(executable, argv):
    # note that before calling setup_bootstrap_path, we are limited because we
    # cannot import stdlib modules. In particular, we cannot use unicode
    # stuffs (because we need to be able to import encodings) and we cannot
    # import os, which is used a bit everywhere in app_main, but only imported
    # *after* setup_bootstrap_path
    setup_bootstrap_path(executable)
    sys.pypy_initfsencoding()
    try:
        cmdline = parse_command_line(argv)
    except CommandLineError as e:
        initstdio()
        print_error(str(e))
        return 2
    except SystemExit as e:
        return e.code or 0
    setup_and_fix_paths(**cmdline)
    return run_command_line(**cmdline)


if __name__ == '__main__':
    # obscure! try removing the following line, see how it crashes, and
    # guess why...
    ImStillAroundDontForgetMe = sys.modules['__main__']

    if len(sys.argv) > 1 and sys.argv[1] == '--argparse-only':
        import io
        del sys.argv[:2]
        sys.stdout = sys.stderr = io.StringIO()
        try:
            options = parse_command_line(sys.argv)
        except SystemExit:
            print('SystemExit', file=sys.__stdout__)
            print(sys.stdout.getvalue(), file=sys.__stdout__)
            raise
        except BaseException as e:
            print('Error', file=sys.__stdout__)
            raise
        else:
            print('Return', file=sys.__stdout__)
        print(options, file=sys.__stdout__)
        print(sys.argv, file=sys.__stdout__)

    # Testing python on python is hard:
    # Some code above (run_command_line) will create a new module
    # named __main__ and store it into sys.modules.  There it will
    # replace the __main__ module that CPython created to execute the
    # lines you are currently reading. This will free the module, and
    # all globals (os, sys...) will be set to None.
    # To avoid this we make a copy of our __main__ module.
    sys.modules['__cpython_main__'] = sys.modules['__main__']

    # debugging only
    def pypy_find_executable(s):
        import os
        return os.path.abspath(s)

    def pypy_find_stdlib(s):
        from os.path import abspath, join, dirname as dn
        thisfile = abspath(__file__)
        root = dn(dn(dn(thisfile)))
        return [join(root, 'lib-python', '3'),
                join(root, 'lib_pypy')]

    def pypy_resolvedirof(s):
        # we ignore the issue of symlinks; for tests, the executable is always
        # interpreter/app_main.py anyway
        import os
        return os.path.abspath(os.path.join(s, '..'))

    import os
    reset = []
    if 'PYTHONINSPECT_' in os.environ:
        reset.append(('PYTHONINSPECT', os.environ.get('PYTHONINSPECT', '')))
        os.environ['PYTHONINSPECT'] = os.environ['PYTHONINSPECT_']
    if 'PYTHONWARNINGS_' in os.environ:
        reset.append(('PYTHONWARNINGS', os.environ.get('PYTHONWARNINGS', '')))
        os.environ['PYTHONWARNINGS'] = os.environ['PYTHONWARNINGS_']
    del os # make sure that os is not available globally, because this is what
           # happens in "real life" outside the tests

    # when run as __main__, this module is often executed by a Python
    # interpreter that have a different list of builtin modules.
    # Make some tests happy by loading them before we clobber sys.path
    import runpy
    if 'time' not in sys.builtin_module_names:
        import time; del time
    if 'operator' not in sys.builtin_module_names:
        import operator; del operator

    # no one should change to which lists sys.argv and sys.path are bound
    old_argv = sys.argv
    old_path = sys.path

    old_streams = sys.stdin, sys.stdout, sys.stderr
    del sys.stdin, sys.stdout, sys.stderr

    sys.pypy_find_executable = pypy_find_executable
    sys.pypy_find_stdlib = pypy_find_stdlib
    sys.pypy_resolvedirof = pypy_resolvedirof
    sys.pypy_initfsencoding = lambda: None
    sys.cpython_path = sys.path[:]

    try:
        sys.exit(int(entry_point(sys.argv[0], sys.argv[1:])))
    finally:
        # restore the normal prompt (which was changed by _pypy_interact), in
        # case we are dropping to CPython's prompt
        sys.stdin, sys.stdout, sys.stderr = old_streams
        sys.ps1 = '>>> '
        sys.ps2 = '... '
        import os; os.environ.update(reset)
        assert old_argv is sys.argv
        assert old_path is sys.path
