class AppTestStringIO:
    def test_stringio(self):
        import io
        sio = io.StringIO()
        sio.write(u'Hello ')
        sio.write(u'world')
        assert sio.getvalue() == u'Hello world'

        assert io.StringIO(u"hello").read() == u'hello'

    def test_capabilities(self):
        import io
        sio = io.StringIO()
        assert sio.readable()
        assert sio.writable()
        assert sio.seekable()
        assert not sio.isatty()
        assert not sio.closed
        assert not sio.line_buffering
        sio.close()
        assert sio.readable()
        assert sio.writable()
        assert sio.seekable()
        raises(ValueError, sio.isatty)
        assert sio.closed
        assert sio.errors is None

    def test_closed(self):
        import io
        sio = io.StringIO()
        sio.close()
        raises(ValueError, sio.read, 1)
        raises(ValueError, sio.write, u"text")

    def testRead(self):
        import io
        buf = u"1234567890"
        sio = io.StringIO(buf)

        assert buf[:1] == sio.read(1)
        assert buf[1:5] == sio.read(4)
        assert buf[5:] == sio.read(900)
        assert u"" == sio.read()

    def test_seek(self):
        import io

        s = u"1234567890"
        sio = io.StringIO(s)

        sio.read(5)
        sio.seek(0)
        r = sio.read()
        assert r == s

        sio.seek(3)
        r = sio.read()
        assert r == s[3:]
        raises(TypeError, sio.seek, 0.0)

        exc_info = raises(ValueError, sio.seek, -3)
        assert exc_info.value.args[0] == "negative seek position: -3"

        raises(ValueError, sio.seek, 3, -1)
        raises(ValueError, sio.seek, 3, -3)

        sio.close()
        raises(ValueError, sio.seek, 0)

    def test_overseek(self):
        import io

        s = u"1234567890"
        sio = io.StringIO(s)

        res = sio.seek(11)
        assert res == 11
        res = sio.read()
        assert res == u""
        assert sio.tell() == 11
        assert sio.getvalue() == s
        sio.write(u"")
        assert sio.getvalue() == s
        sio.write(s)
        assert sio.getvalue() == s + u"\0" + s

    def test_tell(self):
        import io

        s = u"1234567890"
        sio = io.StringIO(s)

        assert sio.tell() == 0
        sio.seek(5)
        assert sio.tell() == 5
        sio.seek(10000)
        assert sio.tell() == 10000

        sio.close()
        raises(ValueError, sio.tell)

    def test_truncate(self):
        import io

        s = u"1234567890"
        sio = io.StringIO(s)

        raises(ValueError, sio.truncate, -1)
        sio.seek(6)
        res = sio.truncate()
        assert res == 6
        assert sio.getvalue() == s[:6]
        res = sio.truncate(4)
        assert res == 4
        assert sio.getvalue() == s[:4]
        # truncate() accepts long objects
        res = sio.truncate(4L)
        assert res == 4
        assert sio.getvalue() == s[:4]
        assert sio.tell() == 6
        sio.seek(0, 2)
        sio.write(s)
        assert sio.getvalue() == s[:4] + s
        pos = sio.tell()
        res = sio.truncate(None)
        assert res == pos
        assert sio.tell() == pos
        raises(TypeError, sio.truncate, '0')
        sio.close()
        raises(ValueError, sio.truncate, 0)

    def test_write_error(self):
        import io

        exc_info = raises(TypeError, io.StringIO, 3)
        assert "int" in exc_info.value.args[0]

        sio = io.StringIO(u"")
        exc_info = raises(TypeError, sio.write, 3)
        assert "int" in exc_info.value.args[0]

    def test_module(self):
        import io

        assert io.StringIO.__module__ == "_io"

    def test_newline_none(self):
        import io

        sio = io.StringIO(u"a\nb\r\nc\rd", newline=None)
        res = list(sio)
        assert res == [u"a\n", u"b\n", u"c\n", u"d"]
        sio.seek(0)
        res = sio.read(1)
        assert res == u"a"
        res = sio.read(2)
        assert res == u"\nb"
        res = sio.read(2)
        assert res == u"\nc"
        res = sio.read(1)
        assert res == u"\n"

        sio = io.StringIO(newline=None)
        res = sio.write(u"a\n")
        assert res == 2
        res = sio.write(u"b\r\n")
        assert res == 3
        res = sio.write(u"c\rd")
        assert res == 3
        sio.seek(0)
        res = sio.read()
        assert res == u"a\nb\nc\nd"
        sio = io.StringIO(u"a\r\nb", newline=None)
        res = sio.read(3)
        assert res == u"a\nb"

    def test_newline_empty(self):
        import io

        sio = io.StringIO(u"a\nb\r\nc\rd", newline="")
        res = list(sio)
        assert res == [u"a\n", u"b\r\n", u"c\r", u"d"]
        sio.seek(0)
        res = sio.read(4)
        assert res == u"a\nb\r"
        res = sio.read(2)
        assert res == u"\nc"
        res = sio.read(1)
        assert res == u"\r"

        sio = io.StringIO(newline="")
        res = sio.write(u"a\n")
        assert res == 2
        res = sio.write(u"b\r")
        assert res == 2
        res = sio.write(u"\nc")
        assert res == 2
        res = sio.write(u"\rd")
        assert res == 2
        sio.seek(0)
        res = list(sio)
        assert res == [u"a\n", u"b\r\n", u"c\r", u"d"]

    def test_newline_lf(self):
        import io

        sio = io.StringIO(u"a\nb\r\nc\rd")
        res = list(sio)
        assert res == [u"a\n", u"b\r\n", u"c\rd"]

    def test_newline_cr(self):
        import io

        sio = io.StringIO(u"a\nb\r\nc\rd", newline="\r")
        res = sio.read()
        assert res == u"a\rb\r\rc\rd"
        sio.seek(0)
        res = list(sio)
        assert res == [u"a\r", u"b\r", u"\r", u"c\r", u"d"]

    def test_newline_crlf(self):
        import io

        sio = io.StringIO(u"a\nb\r\nc\rd", newline="\r\n")
        res = sio.read()
        assert res == u"a\r\nb\r\r\nc\rd"
        sio.seek(0)
        res = list(sio)
        assert res == [u"a\r\n", u"b\r\r\n", u"c\rd"]

    def test_newline_property(self):
        import io

        sio = io.StringIO(newline=None)
        assert sio.newlines is None
        sio.write(u"a\n")
        assert sio.newlines == "\n"
        sio.write(u"b\r\n")
        assert sio.newlines == ("\n", "\r\n")
        sio.write(u"c\rd")
        assert sio.newlines == ("\r", "\n", "\r\n")

    def test_iterator(self):
        import io

        s = u"1234567890\n"
        sio = io.StringIO(s * 10)

        assert iter(sio) is sio
        assert hasattr(sio, "__iter__")
        assert hasattr(sio, "next")

        i = 0
        for line in sio:
            assert line == s
            i += 1
        assert i == 10
        sio.seek(0)
        i = 0
        for line in sio:
            assert line == s
            i += 1
        assert i == 10
        sio = io.StringIO(s * 2)
        sio.close()
        raises(ValueError, next, sio)

    def test_getstate(self):
        import io

        sio = io.StringIO()
        state = sio.__getstate__()
        assert len(state) == 4
        assert isinstance(state[0], unicode)
        assert isinstance(state[1], str)
        assert isinstance(state[2], int)
        assert isinstance(state[3], dict)
        sio.close()
        raises(ValueError, sio.__getstate__)

    def test_setstate(self):
        import io

        sio = io.StringIO()
        sio.__setstate__((u"no error", u"\n", 0, None))
        sio.__setstate__((u"no error", u"", 0, {"spam": 3}))
        raises(ValueError, sio.__setstate__, (u"", u"f", 0, None))
        raises(ValueError, sio.__setstate__, (u"", u"", -1, None))
        raises(TypeError, sio.__setstate__, ("", u"", 0, None))
        raises(TypeError, sio.__setstate__, (u"", u"", 0.0, None))
        raises(TypeError, sio.__setstate__, (u"", u"", 0, 0))
        raises(TypeError, sio.__setstate__, (u"len-test", 0))
        raises(TypeError, sio.__setstate__)
        raises(TypeError, sio.__setstate__, 0)
        sio.close()
        raises(ValueError, sio.__setstate__, (u"closed", u"", 0, None))
