class AppTestWinConsoleIO:
    spaceconfig = dict(usemodules=['_io', '_locale', 'array'])

    def setup_class(cls):
        from rpython.rlib.rarithmetic import INT_MAX, UINT_MAX
        space = cls.space
        cls.w_INT_MAX = space.wrap(INT_MAX)
        cls.w_UINT_MAX = space.wrap(UINT_MAX)

    def test_open_fd(self):
        self.assertRaisesRegex(ValueError,
            "negative file descriptor", _io._WindowsConsoleIO, -1)

        fd, _ = tempfile.mkstemp()
        try:
            # Windows 10: "Cannot open non-console file"
            # Earlier: "Cannot open console output buffer for reading"
            self.assertRaisesRegex(ValueError,
                "Cannot open (console|non-console file)", _io._WindowsConsoleIO, fd)
        finally:
            os.close(fd)

        try:
            f = _io._WindowsConsoleIO(0)
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            self.assertTrue(f.readable())
            self.assertFalse(f.writable())
            self.assertEqual(0, f.fileno())
            f.close()   # multiple close should not crash
            f.close()

        try:
            f = _io._WindowsConsoleIO(1, 'w')
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            self.assertFalse(f.readable())
            self.assertTrue(f.writable())
            self.assertEqual(1, f.fileno())
            f.close()
            f.close()

        try:
            f = _io._WindowsConsoleIO(2, 'w')
        except ValueError:
            # cannot open console because it's not a real console
            pass
        else:
            self.assertFalse(f.readable())
            self.assertTrue(f.writable())
            self.assertEqual(2, f.fileno())
            f.close()
            f.close()

    def test_constructor(self):
        import _io
        t = _io._WindowsConsoleIO("CONIN$")
