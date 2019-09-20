from rpython.tool.udir import udir

class AppTestWinConsoleIO:
    spaceconfig = dict(usemodules=['_io'])

    def setup_method(self, meth):
        tmpfile = udir.join('tmpfile')
        tmpfile.write("a\nb\nc", mode='wb')
        self.tmpfile = tmpfile    
        self.conout_path = self.space.wrap(str(udir.join('CONOUT$')))

    def test_open_fd(self):
        import _io

        w_fd = self.tempfile.fileno()
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

        f = open('C:/con', 'rb', buffering=0)
        assert f is _io._WindowsConsoleIO
        f.close()

    def test_conin_conout_names(self):
        import _io
        f = open(r'\\.\conin$', 'rb', buffering=0)
        assert type(f) is _io._WindowsConsoleIO
        f.close()

        f = open('//?/conout$', 'wb', buffering=0)
        assert type(f) is _io._WindowsConsoleIO
        f.close()
        
    def test_conout_path(self):
        import _io

        with open(self.conout_path, 'wb', buffering=0) as f:
            assert type(f) is _io._WindowsConsoleIO
            
    def test_write_empty_data(self):
        import _io
        with _io._WindowsConsoleIO('CONOUT$', 'w') as f:
            assert f.write(b'') == 0