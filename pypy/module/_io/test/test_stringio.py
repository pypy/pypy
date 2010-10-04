class AppTestStringIO:
    def test_stringio(self):
        import io
        sio = io.StringIO()
        sio.write(u'Hello ')
        sio.write(u'world')
        assert sio.getvalue() == u'Hello world'
