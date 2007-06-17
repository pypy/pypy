
from pypy.translator.c.test.test_genc import compile
from pypy.module._curses import interp_curses
from pypy.module._curses import fficurses        
from pypy.conftest import gettestobjspace
from pypy.tool.autopath import pypydir
from pypy.tool.udir import udir
import py
import sys

class TestCurses(object):
    """ We need to fork here, to prevent
    the setup to be done
    """
    def _spawn(self, *args, **kwds):
        import pexpect
        print 'SPAWN:', args, kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        py_py = py.path.local(pypydir).join('bin', 'py.py')
        return self._spawn(sys.executable, [str(py_py)] + argv)

    def setup_class(self):
        try:
            import pexpect
        except ImportError:
            py.test.skip('pexpect not found')

    def test_setupterm(self):
        source = py.code.Source("""
        import _curses
        try:
            _curses.tigetstr('cup')
        except _curses.error:
            print 'ok!'
        """)
        f = udir.join("test_setupterm.py")
        f.write(source)
        child = self.spawn(['--withmod-_curses', str(f)])
        child.expect('ok!')

    def test_tigetstr(self):
        source = py.code.Source("""
        import _curses
        _curses.setupterm()
        assert _curses.tigetstr('cup') == '\x1b[%i%p1%d;%p2%dH'
        print 'ok!'
        """)
        f = udir.join("test_tigetstr.py")
        f.write(source)
        child = self.spawn(['--withmod-_curses', str(f)])
        child.expect('ok!')

    def test_tparm(self):
        source = py.code.Source("""
        import _curses
        _curses.setupterm()
        assert _curses.tparm(_curses.tigetstr('cup'), 5, 3) == '\033[6;4H'
        print 'ok!'
        """)
        f = udir.join("test_tparm.py")
        f.write(source)
        child = self.spawn(['--withmod-_curses', str(f)])
        child.expect('ok!')
        

# XXX probably we need to run all the stuff here in pexpect anyway...

class TestCCurses(object):
    """ Test compiled version
    """
    def test_csetupterm(self):
        def runs_setupterm():
            interp_curses._curses_setupterm_null(1)

        fn = compile(runs_setupterm, [])
        fn()

    def test_ctgetstr(self):
        def runs_ctgetstr():
            interp_curses._curses_setupterm("xterm", 1)
            res = interp_curses._curses_tigetstr('cup')
            assert res == '\x1b[%i%p1%d;%p2%dH'

        fn = compile(runs_ctgetstr, [])
        fn()

    def test_ctparm(self):
        def runs_tparm():
            interp_curses._curses_setupterm("xterm", 1)
            cup = interp_curses._curses_tigetstr('cup')
            res = interp_curses._curses_tparm(cup, [5, 3])
            assert res == '\033[6;4H'

        fn = compile(runs_tparm, [])
        fn(expected_extra_mallocs=-1)
