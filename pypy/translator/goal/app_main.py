# App-level version of py.py.
# XXX very incomplete!  Blindly runs the file named as first argument.
# No option checking, no interactive console, no fancy hooks.

def entry_point(executable, argv):
    import sys
    sys.executable = executable
    sys.argv = argv
    # with PyPy in top of CPython we can only have around 100 
    # but we need more in the translated PyPy for the compiler package 
    sys.setrecursionlimit(5000)

    mainmodule = type(sys)('__main__')
    sys.modules['__main__'] = mainmodule

    try:
        if argv:
            execfile(sys.argv[0], mainmodule.__dict__)
        else: 
            print >> sys.stderr, "importing code" 
            import code
            print >> sys.stderr, "calling code.interact()"
            code.interact(local=mainmodule.__dict__)
    except:
        excinfo = sys.exc_info()
        typ, val, tb = excinfo 
        print >> sys.stderr, "exception-type:", typ.__name__
        print >> sys.stderr, "exception-value:", str(val)
        # print short tracebacks filename:lineno 
        tbentry = tb
        while tbentry: 
            lineno = tbentry.tb_lineno 
            filename = tbentry.tb_frame.f_code.co_filename
            print >>sys.stderr, "  %s:%d" %(filename, lineno)
            tbentry = tbentry.tb_next 
        # then take forever trying to print a traceback ...
        #sys.excepthook(typ, val, tb)
        return 1
    else:
        return 0

if __name__ == '__main__':
    # debugging only
    import sys
    sys.exit(entry_point(sys.argv[1:]))
