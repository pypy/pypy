
import py
import sys
import os

from pypy.tool.autopath import pypydir
from pypy.translator.c.test.test_genc import compile
from pypy.tool.udir import udir

def setup_module(mod):
    try:
        import pexpect
        mod.pexpect = pexpect
    except ImportError:
        py.test.skip("Pexpect not found")
    try:
        import termios
        mod.termios = termios
    except ImportError:
        py.test.skip("termios not found")
    py_py = py.path.local(pypydir).join('bin', 'py.py')
    assert py_py.check()
    mod.py_py = py_py

class TestTermios(object):
    def _spawn(self, *args, **kwds):
        print 'SPAWN:', args, kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        return self._spawn(sys.executable, argv)

    def test_tcgetattr(self):
        source = py.code.Source("""
        import sys
        sys.path.insert(0, '%s')
        from pypy.translator.c.test.test_genc import compile
        import termios
        from pypy.rlib import rtermios
        def runs_tcgetattr():
            tpl = list(rtermios.tcgetattr(2)[:-1])
            print tpl

        fn = compile(runs_tcgetattr, [], backendopt=False,
)
        print 'XXX'
        fn(expected_extra_mallocs=1)
        print str(rtermios.tcgetattr(2)[:-1])
        """ % os.path.dirname(pypydir))
        f = udir.join("test_tcgetattr.py")
        f.write(source)
        child = self.spawn([str(f)])
        child.expect("XXX")
        child.expect('\[([^\]]*)\]')
        first = child.match.group(1)
        child.expect('\(([^\]]*)\)')
        second = child.match.group(1)
        assert first == second

    def test_tcgetattr2(self):
        source = py.code.Source("""
        import sys
        sys.path.insert(0, '%s')
        from pypy.translator.c.test.test_genc import compile
        from pypy.rpython.module import ll_termios
        from pypy.rlib import rtermios
        import termios
        def runs_tcgetattr():
            try:
                rtermios.tcgetattr(338)
            except termios.error, e:
                return 2
            return 3

        fn = compile(runs_tcgetattr, [], backendopt=False)
        res = fn()
        if res == 2:
            print 'OK!'
        else:
            print 'fail!'
        """ % os.path.dirname(pypydir))
        f = udir.join("test_tcgetattr.py")
        f.write(source)
        child = self.spawn([str(f)])
        child.expect("OK!")

    def test_tcsetattr(self):
        # a test, which doesn't even check anything.
        # I've got no idea how to test it to be honest :-(
        source = py.code.Source("""
        import sys
        sys.path.insert(0, '%s')
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
        print 'OK!'
        """ % os.path.dirname(pypydir))
        f = udir.join("test_tcsetattr.py")
        f.write(source)
        child = self.spawn([str(f)])
        child.expect("OK!")
        
    def test_tcrest(self):
        source = py.code.Source("""
        import sys
        sys.path.insert(0, '%s')
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
        print 'OK!'
        """ % os.path.dirname(pypydir))
        f = udir.join("test_tcall.py")
        f.write(source)
        child = self.spawn([str(f)])
        child.expect("OK!")

    def test_tcsetattr_icanon(self):
        source = py.code.Source("""
        import sys
        sys.path.insert(0, '%s')
        from pypy.rlib import rtermios
        import termios
        old_tcsetattr = termios.tcsetattr
        def check(fd, when, attributes):
            count = len([i for i in attributes[-1] if isinstance(i, int)])
            assert count == 2
        termios.tcsetattr = check
        try:
            attr = list(rtermios.tcgetattr(2))
            attr[3] |= termios.ICANON
            rtermios.tcsetattr(2, termios.TCSANOW, attr)
        finally:
            termios.tcsetattr = old_tcsetattr
        print 'OK!'
        """ % os.path.dirname(pypydir))
        f = udir.join("test_tcsetattricanon.py")
        f.write(source)
        child = self.spawn([str(f)])
        child.expect("OK!")
