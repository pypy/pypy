from pypy.conftest import gettestobjspace

class AppTestTextIO:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])

    def test_constructor(self):
        import _io
        r = _io.BytesIO(b"\xc3\xa9\n\n")
        b = _io.BufferedReader(r, 1000)
        t = _io.TextIOWrapper(b)
        t.__init__(b, encoding="latin1", newline="\r\n")
        assert t.encoding == "latin1"
        assert t.line_buffering == False
        t.__init__(b, encoding="utf8", line_buffering=True)
        assert t.encoding == "utf8"
        assert t.line_buffering == True
        assert t.readline() == u"\xe9\n"
        raises(TypeError, t.__init__, b, newline=42)
        raises(ValueError, t.__init__, b, newline='xyzzy')

