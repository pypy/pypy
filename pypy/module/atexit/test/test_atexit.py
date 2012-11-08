class AppTestAtexit:

    def test_args(self):
        import atexit
        import io
        import sys
        stdout, stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = sys.stderr = capture = io.StringIO()
            def h1():
                print("h1")
            def h2():
                print("h2")
            atexit.register(h1)
            atexit.register(h2)
            atexit._run_exitfuncs()
            assert capture.getvalue() == 'h2\nh1\n'
        finally:
            sys.stdout = stdout
            sys.stderr = stderr
