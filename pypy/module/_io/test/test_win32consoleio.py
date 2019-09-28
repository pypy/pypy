from rpython.tool.udir import udir
from pypy.module._io import interp_win32consoleio
import os

class AppTestWinConsoleIO:
    spaceconfig = dict(usemodules=['_io'])

    def setup_method(self, meth):
        tmpfile = udir.join('tmpfile')
        tmpfile.write("a\nb\nc", mode='wb')
        self.w_tmpfile = self.space.wrap(str(tmpfile))   
        self.w_posix = self.space.appexec([], """():
            import %s as m;
            return m""" % os.name)        
        self.w_conout_path = self.space.wrap(str(udir.join('CONOUT$')))

    def test_open_fd(self):
        import _io
        os = self.posix
        fd = os.open(self.tmpfile, os.O_RDONLY, 0o666)
        #w_fd = self.tmpfile.fileno()
        # Windows 10: "Cannot open non-console file"
        # Earlier: "Cannot open console output buffer for reading"
        raises(ValueError, _io._WindowsConsoleIO, fd)

        raises(ValueError, _io._WindowsConsoleIO, -1)

        try:
            f = _io._WindowsConsoleIO(0)
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            assert f.readable()
            assert not f.writable()
            assert 0 == f.fileno()
            f.close()   # multiple close should not crash
            f.close()

        try:
            f = _io._WindowsConsoleIO(1, 'w')
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            assert not f.readable()
            assert f.writable()
            assert 1 == f.fileno()
            f.close()
            f.close()

        try:
            f = _io._WindowsConsoleIO(2, 'w')
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            assert not f.readable()
            assert f.writable()
            assert 2 == f.fileno()
            f.close()
            f.close()

    def test_constructor(self):
        import _io

        f = _io._WindowsConsoleIO("CON")
        assert f.readable()
        assert not f.writable()
        assert f.fileno() != None
        f.close()   # multiple close should not crash
        f.close()

        f = _io._WindowsConsoleIO('CONIN$')
        assert f.readable()
        assert not f.writable()
        assert f.fileno() != None
        f.close()
        f.close()

        f = _io._WindowsConsoleIO('CONOUT$', 'w')
        assert not f.readable()
        assert f.writable()
        assert f.fileno() != None
        f.close()
        f.close()

        f = open('C:\\con', 'rb', buffering=0)
        assert isinstance(f,_io._WindowsConsoleIO)
        f.close()

    def test_conin_conout_names(self):
        import _io
        f = open(r'\\.\conin$', 'rb', buffering=0)
        assert type(f) is _io._WindowsConsoleIO
        f.close()

        f = open('//?/conout$', 'wb', buffering=0)
        assert isinstance(f , _io._WindowsConsoleIO)
        f.close()
        
    def test_conout_path(self):
        import _io

        with open(self.conout_path, 'wb', buffering=0) as f:
            assert type(f) is _io._WindowsConsoleIO
            
    def test_write_empty_data(self):
        import _io
        with _io._WindowsConsoleIO('CONOUT$', 'w') as f:
            assert f.write(b'') == 0
            
            
class TestGetConsoleType:
    def test_conout(self, space):
        w_file = space.newtext('CONOUT$')
        consoletype = interp_win32consoleio._pyio_get_console_type(space, w_file)
        assert consoletype == 'w'

    def test_conin(self, space):
        w_file = space.newtext('CONIN$')
        consoletype = interp_win32consoleio._pyio_get_console_type(space, w_file)
        assert consoletype == 'r'
        
    def test_con(self, space):
        w_file = space.newtext('CON')
        consoletype = interp_win32consoleio._pyio_get_console_type(space, w_file)
        assert consoletype == 'x'

    def test_conin2(self, space):
        w_file = space.newtext('\\\\.\\conin$')
        consoletype = interp_win32consoleio._pyio_get_console_type(space, w_file)
        assert consoletype == 'r'        
        
    def test_con2(self, space):
        w_file = space.newtext('\\\\?\\con')
        consoletype = interp_win32consoleio._pyio_get_console_type(space, w_file)
        assert consoletype == 'x'