from pypy.conftest import gettestobjspace
from pypy.module.pyexpat.interp_pyexpat import global_storage
from pytest import skip

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

        exc = raises(pyexpat.ExpatError, p.Parse, "3")
        assert exc.value.lineno == 1
        assert exc.value.offset == 11
        assert exc.value.code == 9 # XML_ERROR_JUNK_AFTER_DOC_ELEMENT

        pyexpat.ExpatError("error")

    def test_version(self):
        import pyexpat
        assert isinstance(pyexpat.__version__, str)
        assert pyexpat.EXPAT_VERSION.startswith('expat_')
        assert isinstance(pyexpat.version_info, tuple)
        assert isinstance(pyexpat.version_info[0], int)

    def test_malformed_xml(self):
        import sys
        if sys.platform == "darwin":
            skip("Fails with the version of expat on Mac OS 10.6.6")
        import pyexpat
        xml = "\0\r\n"
        parser = pyexpat.ParserCreate()
        raises(pyexpat.ExpatError, "parser.Parse(xml, True)")

    def test_encoding_argument(self):
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

    def test_encoding_xml(self):
        # use one of the few encodings built-in in expat
        xml = "<?xml version='1.0' encoding='iso-8859-1'?><s>caf\xe9</s>"
        import pyexpat
        p = pyexpat.ParserCreate()
        def gotText(text):
            assert text == u"caf\xe9"
        p.CharacterDataHandler = gotText
        assert p.returns_unicode
        p.Parse(xml)

    def test_explicit_encoding(self):
        xml = "<?xml version='1.0'?><s>caf\xe9</s>"
        import pyexpat
        p = pyexpat.ParserCreate(encoding='iso-8859-1')
        def gotText(text):
            assert text == u"caf\xe9"
        p.CharacterDataHandler = gotText
        p.Parse(xml)

    def test_python_encoding(self):
        # This name is not knonwn by expat
        xml = "<?xml version='1.0' encoding='latin1'?><s>caf\xe9</s>"
        import pyexpat
        p = pyexpat.ParserCreate()
        def gotText(text):
            assert text == u"caf\xe9"
        p.CharacterDataHandler = gotText
        p.Parse(xml)

    def test_decode_error(self):
        xml = '<fran\xe7ais>Comment \xe7a va ? Tr\xe8s bien ?</fran\xe7ais>'
        import pyexpat
        p = pyexpat.ParserCreate()
        def f(*args): pass
        p.StartElementHandler = f
        exc = raises(UnicodeDecodeError, p.Parse, xml)
        assert exc.value.start == 4

    def test_external_entity(self):
        xml = ('<!DOCTYPE doc [\n'
               '  <!ENTITY test SYSTEM "whatever">\n'
               ']>\n'
               '<doc>&test;</doc>')
        import pyexpat
        p = pyexpat.ParserCreate()
        def handler(*args):
            # context, base, systemId, publicId
            assert args == ('test', None, 'whatever', None)
            return True
        p.ExternalEntityRefHandler = handler
        p.Parse(xml)

    def test_errors(self):
        import types
        import pyexpat
        assert isinstance(pyexpat.errors, types.ModuleType)
        # check a few random errors
        assert pyexpat.errors.XML_ERROR_SYNTAX == 'syntax error'
        assert (pyexpat.errors.XML_ERROR_INCORRECT_ENCODING ==
               'encoding specified in XML declaration is incorrect')
        assert (pyexpat.errors.XML_ERROR_XML_DECL ==
                'XML declaration not well-formed')
