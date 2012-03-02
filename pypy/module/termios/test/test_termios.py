
import py
import sys
from pypy.conftest import gettestobjspace
from pypy.tool.autopath import pypydir
from pypy.tool.udir import udir

class TestTermios(object):
    def setup_class(cls):
        try:
            import pexpect
        except ImportError:
            py.test.skip("Pexpect not found")
        try:
            import termios
        except ImportError:
            py.test.skip("termios not found")
        py_py = py.path.local(pypydir).join('bin', 'py.py')
        assert py_py.check()
        cls.py_py = py_py
        cls.termios = termios
        cls.pexpect = pexpect

    def _spawn(self, *args, **kwds):
        print 'SPAWN:', args, kwds
        child = self.pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        return self._spawn(sys.executable, [str(self.py_py)] + argv)

    def test_one(self):
        child = self.spawn(['--withmod-termios'])
        child.expect("Python ")
        child.expect('>>> ')
        child.sendline('import termios')
        child.expect('>>> ')
        child.sendline('termios.tcgetattr(0)')
        child.expect('\[.*?\[.*?\]\]')
        lst = eval(child.match.group(0))
        assert len(lst) == 7
        assert len(lst[-1]) == 32 # XXX is this portable???

    def test_tcall(self):
        """ Again - a test that doesnt really test anything
        """
        source = py.code.Source("""
        import termios
        f = termios.tcgetattr(2)
        termios.tcsetattr(2, termios.TCSANOW, f)
        termios.tcsendbreak(2, 0)
        termios.tcdrain(2)
        termios.tcflush(2, termios.TCIOFLUSH)
        termios.tcflow(2, termios.TCOON)
        print 'ok!'
        """)
        f = udir.join("test_tcall.py")
        f.write(source)
        child = self.spawn(['--withmod-termios', str(f)])
        child.expect('ok!')

    def test_tcsetattr(self):
        source = py.code.Source("""
        import sys
        import termios
        termios.tcsetattr(sys.stdin, 1, [16640, 4, 191, 2608, 15, 15, ['\x03', '\x1c', '\x7f', '\x15', '\x04', 0, 1, '\x00', '\x11', '\x13', '\x1a', '\x00', '\x12', '\x0f', '\x17', '\x16', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00']])
        print 'ok!'
        """)
        f = udir.join("test_tcsetattr.py")
        f.write(source)
        child = self.spawn(['--withmod-termios', str(f)])
        child.expect('ok!')

    def test_ioctl_termios(self):
        source = py.code.Source("""
        import termios
        import fcntl
        lgt = len(fcntl.ioctl(2, termios.TIOCGWINSZ, '\000'*8))
        assert lgt == 8
        print 'ok!'
        """)
        f = udir.join("test_ioctl_termios.py")
        f.write(source)
        child = self.spawn(['--withmod-termios', '--withmod-fcntl', str(f)])
        child.expect('ok!')

    def test_icanon(self):
        source = py.code.Source("""
        import termios
        import fcntl
        import termios
        f = termios.tcgetattr(2)
        f[3] |= termios.ICANON
        termios.tcsetattr(2, termios.TCSANOW, f)
        f = termios.tcgetattr(2)
        assert len([i for i in f[-1] if isinstance(i, int)]) == 2
        assert isinstance(f[-1][termios.VMIN], int)
        assert isinstance(f[-1][termios.VTIME], int)
        print 'ok!'
        """)
        f = udir.join("test_ioctl_termios.py")
        f.write(source)
        child = self.spawn(['--withmod-termios', '--withmod-fcntl', str(f)])
        child.expect('ok!')

class AppTestTermios(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['termios'])
        d = {}
        import termios
        for name in dir(termios):
            val = getattr(termios, name)
            if name.isupper() and type(val) is int:
                d[name] = val
        cls.w_orig_module_dict = cls.space.appexec([], "(): return %r" % (d,))

    def test_values(self):
        import termios
        d = {}
        for name in dir(termios):
            val = getattr(termios, name)
            if name.isupper() and type(val) is int:
                d[name] = val
        assert d == self.orig_module_dict

    def test_error(self):
        import termios, errno, os
        fd = os.open('.', 0)
        try:
            exc = raises(termios.error, termios.tcgetattr, fd)
            assert exc.value.args[0] == errno.ENOTTY
        finally:
            os.close(fd)

    def test_error_tcsetattr(self):
        import termios
        raises(ValueError, termios.tcsetattr, 0, 1, (1, 2))
