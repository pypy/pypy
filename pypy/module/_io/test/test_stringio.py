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
        sio.close()

    def test_closed(self):
        import io
        sio = io.StringIO()
        sio.close()
        raises(ValueError, sio.read, 1)
        raises(ValueError, sio.write, u"text")
