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

    def test_load_string(self):
        import _fastjson
        res = _fastjson.loads('"hello"')
        assert res == u'hello'
        assert type(res) is unicode

    def test_load_string_utf8(self):
        import _fastjson
        s = u'àèìòù'
        res = _fastjson.loads('"%s"' % s.encode('utf-8'))
        assert res == s
