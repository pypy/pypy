from pypy.conftest import gettestobjspace
from pypy.module.pyexpat.interp_pyexpat import global_storage

class AppTestPyexpat:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['pyexpat'])

    def teardown_class(cls):
        global_storage.clear()

    def test_simple(self):
        import pyexpat
        p = pyexpat.ParserCreate()
        res = p.Parse("<xml></xml>")
        assert res == 1

        raises(pyexpat.ExpatError, p.Parse, "3")

    def test_intern(self):
        import pyexpat
        p = pyexpat.ParserCreate()
        def f(*args): pass
        p.StartElementHandler = f
        p.EndElementHandler = f
        p.Parse("<xml></xml>")
        assert len(p.intern) == 1

    def test_set_buffersize(self):
        import pyexpat, sys
        p = pyexpat.ParserCreate()
        p.buffer_size = 150
        assert p.buffer_size == 150
        raises(TypeError, setattr, p, 'buffer_size', sys.maxint + 1)
