import py
# tests here are run as snippets through a pexpected python subprocess

def setup_module(mod):
    try:
        import termios
        mod.termios = termios
    except ImportError:
        py.test.skip("termios not found")

class ExpectTestLLTermios(object):
    def test_tcgetattr(self):
        from pypy.translator.c.test.test_genc import compile
        import termios
        from pypy.rlib import rtermios
        def runs_tcgetattr():
            tpl = list(rtermios.tcgetattr(2)[:-1])
            return str(tpl)

        fn = compile(runs_tcgetattr, [], backendopt=False)
        res = fn()
        res2 = str(rtermios.tcgetattr(2)[:-1])
        assert res[1:-1] == res2[1:-1]

    def test_tcgetattr2(self):
        from pypy.translator.c.test.test_genc import compile
        from pypy.rpython.module import ll_termios
        from pypy.rlib import rtermios
        import os, errno
        import termios
        def runs_tcgetattr(fd):
            try:
                rtermios.tcgetattr(fd)
            except OSError, e:
                return e.errno
            return 0

        fn = compile(runs_tcgetattr, [int], backendopt=False)
        fd = os.open('.', 0)
        try:
            res = fn(fd)
            assert res == errno.ENOTTY
        finally:
            os.close(fd)

    def test_tcsetattr(self):
        # a test, which doesn't even check anything.
        # I've got no idea how to test it to be honest :-(
        from pypy.translator.c.test.test_genc import compile
        from pypy.rpython.module import ll_termios
        from pypy.rlib import rtermios
        import termios, time
        def runs_tcsetattr():
            tp = rtermios.tcgetattr(2)
            a, b, c, d, e, f, g = tp
            rtermios.tcsetattr(2, rtermios.TCSANOW, (a, b, c, d, e, f, g))
            time.sleep(1)
            tp = rtermios.tcgetattr(2)
            assert tp[5] == f

        fn = compile(runs_tcsetattr, [], backendopt=False)
        fn()

    def test_tcrest(self):
        from pypy.translator.c.test.test_genc import compile
        from pypy.rpython.module import ll_termios
        import termios, time
        def runs_tcall():
            termios.tcsendbreak(2, 0)
            termios.tcdrain(2)
            termios.tcflush(2, termios.TCIOFLUSH)
            termios.tcflow(2, termios.TCOON)

        fn = compile(runs_tcall, [], backendopt=False)
        fn()

    def test_tcsetattr_icanon(self):
        from pypy.rlib import rtermios
        import termios
        def check(fd, when, attributes):
            count = len([i for i in attributes[-1] if isinstance(i, int)])
            assert count == 2
        termios.tcsetattr = check
        attr = list(rtermios.tcgetattr(2))
        attr[3] |= termios.ICANON
        rtermios.tcsetattr(2, termios.TCSANOW, attr)

