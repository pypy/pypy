from rpython.tool.udir import udir
from pypy.interpreter.gateway import interp2app
from pypy.module._io import interp_win32consoleio
from pypy.conftest import option
from rpython.rtyper.lltypesystem import rffi
import os

if os.name != 'nt':
    import pytest
    pytest.skip('Windows only tests')

try:
    import _testconsole
except ImportError:
    from lib_pypy import _testconsole

class AppTestWinConsoleIO:
    spaceconfig = dict(usemodules=['_io', '_cffi_backend'])

    def setup_class(cls):
        tmpfile = udir.join('tmpfile')
        tmpfile.write("a\nb\nc", mode='wb')
        cls.w_tmpfile = cls.space.wrap(str(tmpfile))   
        cls.w_posix = cls.space.appexec([], """():
            import %s as m;
            return m""" % os.name)
        cls.w_conout_path = cls.space.wrap(str(udir.join('CONOUT$')))
        if option.runappdirect:
            cls.w_write_input = _testconsole.write_input
        else:
            def cls_write_input(space, w_module, w_console, w_s):
                module = space.unwrap(w_module)
                handle = rffi.cast(rffi.INT_real, w_console.handle)
                s = space.utf8_w(w_s).decode('utf-8')
                return space.wrap(_testconsole.write_input(module, handle, s))
            cls.w_write_input = cls.space.wrap(interp2app(cls_write_input))

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
            
    def test_partial_reads(self):
        import _io
        source = b'abcedfg'
        actual = b''
        with open('CONIN$', 'rb', buffering=0) as stdin:
            self.write_input(None, stdin, source)
            while not actual.endswith(b'\n'):
                b = stdin.read(len(source))
                print('read', b)
                if not b:
                    break
                actual += b

        assert actual == source


            
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
