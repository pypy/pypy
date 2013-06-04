# -*- encoding: utf-8 -*-
import py
from pypy.module._fastjson.interp_decoder import JSONDecoder

def test_skip_whitespace():
    dec = JSONDecoder('fake space', '   hello   ')
    assert dec.i == 0
    dec.skip_whitespace()
    assert dec.next() == 'h'
    assert dec.next() == 'e'
    assert dec.next() == 'l'
    assert dec.next() == 'l'
    assert dec.next() == 'o'
    dec.skip_whitespace()
    assert dec.eof()

    

class AppTest(object):
    spaceconfig = {"objspace.usemodules._fastjson": True}

    def test_decode_string(self):
        import _fastjson
        res = _fastjson.loads('"hello"')
        assert res == u'hello'
        assert type(res) is unicode

    def test_decode_string_utf8(self):
        import _fastjson
        s = u'àèìòù'
        res = _fastjson.loads('"%s"' % s.encode('utf-8'))
        assert res == s

    def test_skip_whitespace(self):
        import _fastjson
        s = '   "hello"   '
        assert _fastjson.loads(s) == u'hello'
        s = '   "hello"   extra'
        raises(ValueError, "_fastjson.loads(s)")

    def test_unterminated_string(self):
        import _fastjson
        s = '"hello' # missing the trailing "
        raises(ValueError, "_fastjson.loads(s)")

    def test_escape_sequence(self):
        import _fastjson
        assert _fastjson.loads(r'"\\"') == u'\\'
        assert _fastjson.loads(r'"\""') == u'"'
        assert _fastjson.loads(r'"\/"') == u'/'       
        assert _fastjson.loads(r'"\b"') == u'\b'
        assert _fastjson.loads(r'"\f"') == u'\f'
        assert _fastjson.loads(r'"\n"') == u'\n'
        assert _fastjson.loads(r'"\r"') == u'\r'
        assert _fastjson.loads(r'"\t"') == u'\t'
