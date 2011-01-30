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
        sio.close()
        assert sio.readable()
        assert sio.writable()
        assert sio.seekable()
        raises(ValueError, sio.isatty)
        assert sio.closed

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
