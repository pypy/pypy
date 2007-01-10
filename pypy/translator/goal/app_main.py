#! /usr/bin/env python
# App-level version of py.py.
# XXX this is probably still incomplete.
"""
options:
  -i           inspect interactively after running script
  -O           dummy optimization flag for compatibility with C Python
  -c CMD       program passed in as CMD (terminates option list)
  -u           unbuffered binary stdout and stderr
  -h, --help   show this help message and exit
  --version    print the PyPy version
  --info       print translation information about this PyPy executable
"""

import sys, os

originalexcepthook = sys.__excepthook__

def run_toplevel(f, *fargs, **fkwds):
    """Calls f() and handle all OperationErrors.
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
            # XXX extra debugging info in case the code below goes very wrong
            # XXX (temporary)
            if hasattr(sys, 'stderr'):
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
            print '   %25s: %s' % (name, value)

def print_help():
    print 'usage: %s [options]' % (sys.executable,)
    print __doc__

def print_error(msg):
    print >> sys.stderr, msg
    print >> sys.stderr, 'usage: %s [options]' % (sys.executable,)
    print >> sys.stderr, 'Try `%s -h` for more information.' % (sys.executable,)

def set_unbuffered_io():
    if os.name == 'nt':
        raise NotImplementedError("binary stdin/stdout not implemented "
                                  "on Windows")
    sys.stdin  = sys.__stdin__  = os.fdopen(0, 'rb', 0)
    sys.stdout = sys.__stdout__ = os.fdopen(1, 'wb', 0)
    sys.stderr = sys.__stderr__ = os.fdopen(2, 'wb', 0)

# ____________________________________________________________
# Main entry point

AUTOSUBPATH = 'share' + os.sep + 'pypy-%d.%d'

def entry_point(executable, argv):
    # find the full path to the executable, assuming that if there is no '/'
    # in the provided one then we must look along the $PATH
    if os.sep not in executable:
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
            break
        newpath = sys.pypy_initial_path(dirname)
        if newpath is None:
            newpath = sys.pypy_initial_path(os.path.join(dirname, autosubpath))
            if newpath is None:
                search = dirname    # walk to the parent directory
                continue
        sys.path = newpath      # found!
        break

    go_interactive = False
    run_command = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if not arg.startswith('-'):
            break
        if arg == '-i':
            go_interactive = True
        elif arg == '-c':
            if i >= len(argv):
                print_error('Argument expected for the -c option')
                return 2
            run_command = True
            break
        elif arg == '-u':
            set_unbuffered_io()
        elif arg == '-O':
            pass
        elif arg == '--version':
            print sys.version
            return 0
        elif arg == '--info':
            print_info()
            return 0
        elif arg == '-h' or arg == '--help':
            print_help()
            return 0
        elif arg == '--':
            i += 1
            break     # terminates option list
        else:
            print_error('unrecognized option %r' % (arg,))
            return 2
        i += 1
    sys.argv = argv[i:]

    # with PyPy in top of CPython we can only have around 100 
    # but we need more in the translated PyPy for the compiler package 
    sys.setrecursionlimit(5000)

    mainmodule = type(sys)('__main__')
    sys.modules['__main__'] = mainmodule

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

    try:
        if sys.argv:
            if run_command:
                cmd = sys.argv.pop(1)
                def run_it():
                    exec cmd in mainmodule.__dict__
                run_toplevel(run_it)
            else:
                scriptdir = resolvedirof(sys.argv[0])
                sys.path.insert(0, scriptdir)
                run_toplevel(execfile, sys.argv[0], mainmodule.__dict__)
        else: 
            sys.argv.append('')
            go_interactive = True
        if go_interactive or os.environ.get('PYTHONINSPECT'):
            print >> sys.stderr, "debug: importing code" 
            import code
            print >> sys.stderr, "debug: calling code.interact()"
            run_toplevel(code.interact, local=mainmodule.__dict__)
    except SystemExit, e:
        return e.code
    else:
        return 0

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

if __name__ == '__main__':
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

    from pypy.module.sys.version import PYPY_VERSION
    sys.pypy_version_info = PYPY_VERSION
    sys.pypy_initial_path = pypy_initial_path
    #sys.exit(entry_point(sys.argv[0], sys.argv[1:]))
    sys.exit(entry_point('app_main.py', sys.argv[1:]))
