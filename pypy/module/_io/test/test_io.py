from pypy.conftest import gettestobjspace

class AppTestIoModule:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_io'])

    def test_import(self):
        import io

    def test_iobase(self):
        import io
        io.IOBase()

        class MyFile(io.BufferedIOBase):
            def __init__(self, filename):
                pass
        MyFile("file")

