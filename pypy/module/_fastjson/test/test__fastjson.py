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

    def test_escape_sequence_in_the_middle(self):
        import _fastjson
        s = r'"hello\nworld"'
        assert _fastjson.loads(s) == "hello\nworld"

    def test_unterminated_string_after_escape_sequence(self):
        import _fastjson
        s = r'"hello\nworld' # missing the trailing "
        raises(ValueError, "_fastjson.loads(s)")
        
    def test_escape_sequence_unicode(self):
        import _fastjson
        s = r'"\u1234"'
        assert _fastjson.loads(s) == u'\u1234'

    def test_decode_numeric(self):
        import _fastjson
        def check(s, val):
            res = _fastjson.loads(s)
            assert type(res) is type(val)
            assert res == val
        #
        check('42', 42)
        check('-42', -42)
        check('42.123', 42.123)
        check('42E0', 42.0)
        check('42E3', 42000.0)
        check('42E-1', 4.2)
        check('42.123E3', 42123.0)

    def test_decode_numeric_invalid(self):
        import _fastjson
        def error(s):
            raises(ValueError, _fastjson.loads, s)
        #
        error('  42   abc')
        error('.123')
        error('12.')
        error('12.-3')
        error('12E')
        error('12E-')


    def test_decode_object(self):
        import _fastjson
        assert _fastjson.loads('{}') == {}
        #
        s = '{"hello": "world", "aaa": "bbb"}'
        assert _fastjson.loads(s) == {'hello': 'world',
                                      'aaa': 'bbb'}

    def test_decode_object_nonstring_key(self):
        import _fastjson
        raises(ValueError, "_fastjson.loads('{42: 43}')")
        
