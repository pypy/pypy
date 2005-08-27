# App-level version of py.py.
# XXX this is probably still incomplete.
"""
options:
  -i           inspect interactively after running script
  -O           dummy optimization flag for compatibility with C Python
  -c CMD       program passed in as CMD (terminates option list)
  -h, --help   show this help message and exit
  --version    print the PyPy version
  --info       print translation information about this PyPy executable
"""

import sys

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
                print >> sys.stderr, "debug: exception-type: ", etype.__name__
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

# ____________________________________________________________
# Main entry point

def entry_point(executable, argv):
    sys.executable = executable
    go_interactive = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if not arg.startswith('-'):
            break
        if arg == '-i':
            go_interactive = True
        elif arg == '-c':
            if i >= len(argv)-1:
                print_error('Argument expected for the -c option')
                return 2
            break
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

    try:
        if sys.argv:
            if sys.argv[0] == '-c':
                cmd = sys.argv.pop(1)
                def run_it():
                    exec cmd in mainmodule.__dict__
                run_toplevel(run_it)
            else:
                run_toplevel(execfile, sys.argv[0], mainmodule.__dict__)
        else: 
            go_interactive = True
        if go_interactive:
            print >> sys.stderr, "debug: importing code" 
            import code
            print >> sys.stderr, "debug: calling code.interact()"
            run_toplevel(code.interact, local=mainmodule.__dict__)
    except SystemExit, e:
        return e.exitcode
    else:
        return 0

if __name__ == '__main__':
    # obscure! try removing the following line, see how it crashes, and
    # guess why...
    ImStillAroundDontForgetMe = sys.modules['__main__']
    # debugging only
    sys.exit(entry_point(sys.argv[0], sys.argv[1:]))
