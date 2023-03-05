import atexit, sys


def test_args():
    import io
    stdout, stderr = sys.stdout, sys.stderr
    nhooks = atexit._ncallbacks()
    try:
        sys.stdout = sys.stderr = capture = io.StringIO()
        def h1():
            print("h1")
        def h2():
            print("h2")
        atexit.register(h1)
        atexit.register(h2)
        assert atexit._ncallbacks() == nhooks + 2
        atexit._run_exitfuncs()
        assert atexit._ncallbacks() == 0 
        assert capture.getvalue() == 'h2\nh1\n'
    finally:
        sys.stdout = stdout
        sys.stderr = stderr


def test_atexit_uses_unraisablehook():
    nhooks = atexit._ncallbacks()

    l = []
    def ownhook(hookargs):
        l.append(hookargs)

    sys.unraisablehook = ownhook
    try:
        def r():
            1/0
        atexit.register(r)
        atexit._run_exitfuncs()
        assert atexit._ncallbacks() == nhooks
        ua = l[0]
        assert ua.exc_type is ZeroDivisionError
        assert ua.object is r
    finally:
        sys.unraisablehook = sys.__unraisablehook__



