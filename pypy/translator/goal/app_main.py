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
  -k, --oldstyle use old-style classes instead of newstyle classes
                 everywhere %(oldstyle)s
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
    details = {'oldstyle': ''}
    if sys.pypy_translation_info['objspace.std.oldstyle']:
        details['oldstyle'] = '[default]'
    print __doc__ % details

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

# faking os, until we really are able to import it from source
"""
Why fake_os ?
-------------

When pypy is starting, the builtin modules are there, but os.path
is a Python module. The current startup code depends on os.py,
which had the side effect that os.py got frozen into the binary.

Os.py is a wrapper for system specific built-in modules and tries
to unify the interface. One problem is os.environ which looks
very differently per os.
Due to the way os.py initializes its environ variable on Windows,
it s hard to get a correct os.getenv that uses the actual environment
variables. In order to fix that without modifying os.py, we need to
re-import it several times, before and after compilation.

When compiling the source, we first create a fake_os class instance.
fake_os contains all of os, when compiling.reduction seems to be not
appropriate, since lots of other modules are sucked in, at the same time.
A complete reduction is possible, but would require much more work.

In the course of creating fake_os, we import the real os. We keep a record
of which modules were imported, before.

During start of the entry_point, we call os.setup().
This repeats an import of the specific parts in os.name.
Depending of the underlying os, this might or might not
cause a redefinition of certain os variables, but this happens
exactly like in os.py's initialization.
We then capture the variable environ, which may or may not come from the
specific os.
After that, we re-initialize our dict to what is expected in standard
os. The effect of all this magic is that we have captured the environ
cariable, again, and we now can redefine os.getenv to use this fresh
variable, being accurate and not frozen.

At this point, we finally can compute the location of our import.

As a side effect, the involved modules are re-imported, although they had
been compiled in, so PyPy behaves really conformant, making all .py
modules changeable, again.
"""

def we_are_translated():
    # this function does not exist on app-level.
    # Don't confuse it with
    # from pypy.rlib.objectmodel import we_are_translated
    # which I did.
    return hasattr(sys, 'pypy_translation_info')

class fake_os:
    def __init__(self):
        import sys
        self.pre_import = sys.modules.keys()
        import os
        self.os = os
        # make ourselves a clone of os
        self.__dict__.update(self.os.__dict__)

    def setup(self):
        # we now repeat the os-specific initialization, which
        # must be done before importing os, since os hides
        # variables after initialization.
        specifics = __import__(self.os.name)
        self.__dict__.update(specifics.__dict__)
        # depending on the os, we now might or might not have
        # a new environ variable. However, we can now
        # repeat the environ initialisation from os.py
        environ = self.os._Environ(self.environ)
        # to be safe, reset our dict to be like os
        self.__dict__.update(self.os.__dict__)
        # but now we insert the fresh environ
        self.environ = environ
        del self.getenv
        # use our method, instead of the os's one's
        assert self.getenv
        
    def teardown(self):
        # re-load modules instead of using the pre-compiled ones
        # note that this gives trouble if we are not translated,
        # since some exithandler in threading.py complains
        # XXX check if this is a bug to be fixed for cpython
        if we_are_translated():
            for mod in sys.modules.keys():
                if mod not in self.pre_import:
                    del sys.modules[mod]
        global os
        import os

    def getenv(self, key, default=None):
        """Get an environment variable, return None if it doesn't exist.
        The optional second argument can specify an alternate default."""
        return self.environ.get(key, default)
        
os = fake_os()

AUTOSUBPATH = 'share' + os.sep + 'pypy-%d.%d'

if 'nt' in sys.builtin_module_names:
    IS_WINDOWS = True
    DRIVE_LETTER_SEP = ':'
else:
    IS_WINDOWS = False

def entry_point(executable, argv):
    # find the full path to the executable, assuming that if there is no '/'
    # in the provided one then we must look along the $PATH
    os.setup() # this is the faked one
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
            break
        newpath = sys.pypy_initial_path(dirname)
        if newpath is None:
            newpath = sys.pypy_initial_path(os.path.join(dirname, autosubpath))
            if newpath is None:
                search = dirname    # walk to the parent directory
                continue
        sys.path = newpath      # found!
        break
    
    os.teardown() # from now on this is the real one
    
    go_interactive = False
    run_command = False
    import_site = True
    i = 0
    run_module = False
    run_stdin = False
    oldstyle_classes = False
    while i < len(argv):
        arg = argv[i]
        if not arg.startswith('-'):
            break
        if arg == '-i':
            go_interactive = True
        elif arg == '-c':
            if i+1 >= len(argv):
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
        elif arg == '-S':
            import_site = False
        elif arg == '-':
            run_stdin = True
            break     # not an option but a file name representing stdin
        elif arg == '-m':
            i += 1
            if i >= len(argv):
                print_error('Argument expected for the -m option')
                return 2
            run_module = True
            break
        elif arg in ('-k', '--oldstyle'):
            oldstyle_classes = True
        elif arg == '--':
            i += 1
            break     # terminates option list
        else:
            print_error('unrecognized option %r' % (arg,))
            return 2
        i += 1
    sys.argv = argv[i:]
    if not sys.argv:
        sys.argv.append('')
        run_stdin = True

    # with PyPy in top of CPython we can only have around 100 
    # but we need more in the translated PyPy for the compiler package 
    sys.setrecursionlimit(5000)

    mainmodule = type(sys)('__main__')
    sys.modules['__main__'] = mainmodule

    if oldstyle_classes:
        import __builtin__
        __builtin__.__metaclass__ = __builtin__._classobj

    if import_site:
        try:
            import site
        except:
            print >> sys.stderr, "'import site' failed"


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

    def is_interactive():
        return go_interactive or os.getenv('PYTHONINSPECT')

    success = True

    try:
        if run_command:
            cmd = sys.argv.pop(1)
            def run_it():
                exec cmd in mainmodule.__dict__
            success = run_toplevel(run_it)
        elif run_module:
            def run_it():
                import runpy
                runpy.run_module(sys.argv[0], None, '__main__', True)
            success = run_toplevel(run_it)
        elif run_stdin:
            if is_interactive() or sys.stdin.isatty():
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
                go_interactive = True
            else:
                def run_it():
                    co_stdin = compile(sys.stdin.read(), '<stdin>', 'exec')
                    exec co_stdin in mainmodule.__dict__
                mainmodule.__file__ = '<stdin>'
                success = run_toplevel(run_it)
        else:
            mainmodule.__file__ = sys.argv[0]
            scriptdir = resolvedirof(sys.argv[0])
            sys.path.insert(0, scriptdir)
            success = run_toplevel(execfile, sys.argv[0], mainmodule.__dict__)
            
        if is_interactive():
            try:
                import _curses
                import termios
                from pyrepl.python_reader import main
                from pyrepl import cmdrepl
                #import pdb
                #pdb.Pdb = cmdrepl.replize(pdb.Pdb, 1)
            except ImportError:
                success = run_toplevel(interactive_console, mainmodule)
            else:
                main(print_banner=False, clear_main=False)
                success = True
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

def interactive_console(mainmodule):
    # some parts of code.py are copied here because it seems to be impossible
    # to start an interactive console without printing at least one line
    # of banner
    import code
    console = code.InteractiveConsole(mainmodule.__dict__)
    try:
        import readline
    except ImportError:
        pass
    more = 0
    while 1:
        try:
            if more:
                prompt = sys.ps2
            else:
                prompt = sys.ps1
            try:
                line = raw_input(prompt)
            except EOFError:
                console.write("\n")
                break
            else:
                more = console.push(line)
        except KeyboardInterrupt:
            console.write("\nKeyboardInterrupt\n")
            console.resetbuffer()
            more = 0


if __name__ == '__main__':
    import autopath
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

    from pypy.module.sys.version import PYPY_VERSION
    sys.pypy_version_info = PYPY_VERSION
    sys.pypy_initial_path = pypy_initial_path
    sys.exit(entry_point(sys.argv[0], sys.argv[1:]))
    #sys.exit(entry_point('app_main.py', sys.argv[1:]))
