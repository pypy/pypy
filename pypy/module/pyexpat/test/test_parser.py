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

    def test_encoding(self):
        import pyexpat
        for encoding_arg in (None, 'utf-8', 'iso-8859-1'):
            for namespace_arg in (None, '{'):
                print encoding_arg, namespace_arg
                p = pyexpat.ParserCreate(encoding_arg, namespace_arg)
                data = []
                p.CharacterDataHandler = lambda s: data.append(s)
                encoding = encoding_arg is None and 'utf-8' or encoding_arg

                res = p.Parse(u"<xml>\u00f6</xml>".encode(encoding), isfinal=True)
                assert res == 1
                assert data == [u"\u00f6"]
