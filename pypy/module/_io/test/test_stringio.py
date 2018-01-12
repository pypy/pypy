class AppTestStringIO:
    def test_stringio(self):
        import io
        sio = io.StringIO()
        sio.write('Hello ')
        sio.write('world')
        assert sio.getvalue() == 'Hello world'

        assert io.StringIO("hello").read() == 'hello'

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
        raises(ValueError, sio.readable)
        raises(ValueError, sio.writable)
        raises(ValueError, sio.seekable)
        raises(ValueError, sio.isatty)
        assert sio.closed
        assert sio.errors is None

    def test_closed(self):
        import io
        sio = io.StringIO()
        sio.close()
        raises(ValueError, sio.read, 1)
        raises(ValueError, sio.write, "text")

    def test_read(self):
        import io
        buf = "1234567890"
        sio = io.StringIO(buf)

        assert buf[:1] == sio.read(1)
        assert buf[1:5] == sio.read(4)
        assert buf[5:] == sio.read(900)
        assert "" == sio.read()

    def test_readline(self):
        import io
        sio = io.StringIO('123\n456')
        assert sio.readline(2) == '12'
        assert sio.readline(None) == '3\n'
        assert sio.readline() == '456'

    def test_seek(self):
        import io

        s = "1234567890"
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

        s = "1234567890"
        sio = io.StringIO(s)

        res = sio.seek(11)
        assert res == 11
        res = sio.read()
        assert res == ""
        assert sio.tell() == 11
        assert sio.getvalue() == s
        sio.write("")
        assert sio.getvalue() == s
        sio.write(s)
        assert sio.getvalue() == s + "\0" + s

    def test_tell(self):
        import io

        s = "1234567890"
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

        s = "1234567890"
        sio = io.StringIO(s)

        raises(ValueError, sio.truncate, -1)
        sio.seek(6)
        res = sio.truncate()
        assert res == 6
        assert sio.getvalue() == s[:6]
        res = sio.truncate(4)
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

        sio = io.StringIO("")
        exc_info = raises(TypeError, sio.write, 3)
        assert "int" in exc_info.value.args[0]

    def test_newline_none(self):
        import io

        sio = io.StringIO("a\nb\r\nc\rd", newline=None)
        res = list(sio)
        assert res == ["a\n", "b\n", "c\n", "d"]
        sio.seek(0)
        res = sio.read(1)
        assert res == "a"
        res = sio.read(2)
        assert res == "\nb"
        res = sio.read(2)
        assert res == "\nc"
        res = sio.read(1)
        assert res == "\n"

        sio = io.StringIO(newline=None)
        res = sio.write("a\n")
        assert res == 2
        res = sio.write("b\r\n")
        assert res == 3
        res = sio.write("c\rd")
        assert res == 3
        sio.seek(0)
        res = sio.read()
        assert res == "a\nb\nc\nd"
        sio = io.StringIO("a\r\nb", newline=None)
        res = sio.read(3)
        assert res == "a\nb"

    def test_newline_empty(self):
        import io

        sio = io.StringIO("a\nb\r\nc\rd", newline="")
        res = list(sio)
        assert res == ["a\n", "b\r\n", "c\r", "d"]
        sio.seek(0)
        res = sio.read(4)
        assert res == "a\nb\r"
        res = sio.read(2)
        assert res == "\nc"
        res = sio.read(1)
        assert res == "\r"

        sio = io.StringIO(newline="")
        res = sio.write("a\n")
        assert res == 2
        res = sio.write("b\r")
        assert res == 2
        res = sio.write("\nc")
        assert res == 2
        res = sio.write("\rd")
        assert res == 2
        sio.seek(0)
        res = list(sio)
        assert res == ["a\n", "b\r\n", "c\r", "d"]

    def test_newline_lf(self):
        import io

        sio = io.StringIO("a\nb\r\nc\rd")
        res = list(sio)
        assert res == ["a\n", "b\r\n", "c\rd"]

    def test_newline_cr(self):
        import io

        sio = io.StringIO("a\nb\r\nc\rd", newline="\r")
        res = sio.read()
        assert res == "a\rb\r\rc\rd"
        sio.seek(0)
        res = list(sio)
        assert res == ["a\r", "b\r", "\r", "c\r", "d"]

    def test_newline_crlf(self):
        import io

        sio = io.StringIO("a\nb\r\nc\rd", newline="\r\n")
        res = sio.read()
        assert res == "a\r\nb\r\r\nc\rd"
        sio.seek(0)
        res = list(sio)
        assert res == ["a\r\n", "b\r\r\n", "c\rd"]

    def test_newline_property(self):
        import io

        sio = io.StringIO(newline=None)
        assert sio.newlines is None
        sio.write("a\n")
        assert sio.newlines == "\n"
        sio.write("b\r\n")
        assert sio.newlines == ("\n", "\r\n")
        sio.write("c\rd")
        assert sio.newlines == ("\r", "\n", "\r\n")

    def test_iterator(self):
        import io

        s = "1234567890\n"
        sio = io.StringIO(s * 10)

        assert iter(sio) is sio
        assert hasattr(sio, "__iter__")
        assert hasattr(sio, "__next__")

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
        sio.seek(len(s) * 10 +1)
        assert list(sio) == []
        sio = io.StringIO(s * 2)
        sio.close()
        raises(ValueError, next, sio)

    def test_getstate(self):
        import io

        sio = io.StringIO()
        state = sio.__getstate__()
        assert len(state) == 4
        assert isinstance(state[0], str)
        assert isinstance(state[1], str)
        assert isinstance(state[2], int)
        assert isinstance(state[3], dict)
        sio.close()
        raises(ValueError, sio.__getstate__)

    def test_setstate(self):
        import io

        sio = io.StringIO()
        sio.__setstate__(("no error", "\n", 0, None))
        sio.__setstate__(("no error", "", 0, {"spam": 3}))
        raises(ValueError, sio.__setstate__, ("", "f", 0, None))
        raises(ValueError, sio.__setstate__, ("", "", -1, None))
        raises(TypeError, sio.__setstate__, (b"", "", 0, None))
        raises(TypeError, sio.__setstate__, ("", "", 0.0, None))
        raises(TypeError, sio.__setstate__, ("", "", 0, 0))
        raises(TypeError, sio.__setstate__, ("len-test", 0))
        raises(TypeError, sio.__setstate__)
        raises(TypeError, sio.__setstate__, 0)
        sio.close()
        raises(ValueError, sio.__setstate__, ("closed", "", 0, None))
