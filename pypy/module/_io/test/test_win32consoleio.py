class AppTestWinConsoleIO:
    spaceconfig = dict(usemodules=['_io', '_locale', 'array'])

    def setup_class(cls):
        from rpython.rlib.rarithmetic import INT_MAX, UINT_MAX
        space = cls.space
        cls.w_INT_MAX = space.wrap(INT_MAX)
        cls.w_UINT_MAX = space.wrap(UINT_MAX)

    def test_constructor(self):
        import _io
        t = _io.WinConsoleIO()
