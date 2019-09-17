class AppTestWinConsoleIO:
    spaceconfig = dict(usemodules=['_io', '_locale', 'array'])

    def setup_class(cls):
        from rpython.rlib.rarithmetic import INT_MAX, UINT_MAX
        space = cls.space
        cls.w_INT_MAX = space.wrap(INT_MAX)
        cls.w_UINT_MAX = space.wrap(UINT_MAX)

    def test_open_fd(self):
        import _io
        raises(ValueError, _io._WindowsConsoleIO, -1)

        fd, _ = tempfile.mkstemp()
        try:
            # Windows 10: "Cannot open non-console file"
            # Earlier: "Cannot open console output buffer for reading"
            raises(ValueError, _io._WindowsConsoleIO, fd)
        finally:
            os.close(fd)

        try:
            f = _io._WindowsConsoleIO(0)
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            assert f.readable() == True
            assert f.writable() == False
            assert 0 == f.fileno()
            f.close()   # multiple close should not crash
            f.close()

        try:
            f = _io._WindowsConsoleIO(1, 'w')
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            assert f.readable() == False
            assert True == f.writable()
            assert 1 == f.fileno()
            f.close()
            f.close()

        try:
            f = _io._WindowsConsoleIO(2, 'w')
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            assert False == f.readable()
            assert True == f.writable()
            assert 2 == f.fileno()
            f.close()
            f.close()

    def test_constructor(self):
        import _io
        t = _io._WindowsConsoleIO("CONIN$")
