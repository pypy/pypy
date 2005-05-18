# App-level version of py.py.
# XXX very incomplete!  Blindly runs the file named as first argument.
# No option checking, no interactive console, no fancy hooks.

def entry_point(argv):
    import sys
    sys.executable = argv[0]
    sys.argv = argv[1:]

    mainmodule = type(sys)('__main__')
    sys.modules['__main__'] = mainmodule

    try:
        execfile(sys.argv[0], mainmodule.__dict__)
    except:
        sys.excepthook(*sys.exc_info())
        return 1
    else:
        return 0

if __name__ == '__main__':
    # debugging only
    import sys
    sys.exit(entry_point(sys.argv))
