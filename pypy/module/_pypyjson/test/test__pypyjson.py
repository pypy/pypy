# -*- encoding: utf-8 -*-
from pypy.module._pypyjson.interp_decoder import JSONDecoder

def test_skip_whitespace():
    s = '   hello   '
    dec = JSONDecoder('fake space', s)
    assert dec.pos == 0
    assert dec.skip_whitespace(0) == 3
    assert dec.skip_whitespace(3) == 3
    assert dec.skip_whitespace(8) == len(s)
    dec.close()

def test_decode_key():
    s1 = "123" * 100
    s = ' "%s"   "%s" ' % (s1, s1)
    dec = JSONDecoder('fake space', s)
    assert dec.pos == 0
    x = dec.decode_key(0)
    assert x == s1
    # check caching
    y = dec.decode_key(dec.pos)
    assert y == s1
    assert y is x
    dec.close()

class AppTest(object):
    spaceconfig = {"objspace.usemodules._pypyjson": True}

    def test_raise_on_unicode(self):
        import _pypyjson
        raises(TypeError, _pypyjson.loads, u"42")


    def test_decode_constants(self):
        import _pypyjson
        assert _pypyjson.loads('null') is None
        raises(ValueError, _pypyjson.loads, 'nul')
        raises(ValueError, _pypyjson.loads, 'nu')
        raises(ValueError, _pypyjson.loads, 'n')
        raises(ValueError, _pypyjson.loads, 'nuXX')
        #
        assert _pypyjson.loads('true') is True
        raises(ValueError, _pypyjson.loads, 'tru')
        raises(ValueError, _pypyjson.loads, 'tr')
        raises(ValueError, _pypyjson.loads, 't')
        raises(ValueError, _pypyjson.loads, 'trXX')
        #
        assert _pypyjson.loads('false') is False
        raises(ValueError, _pypyjson.loads, 'fals')
        raises(ValueError, _pypyjson.loads, 'fal')
        raises(ValueError, _pypyjson.loads, 'fa')
        raises(ValueError, _pypyjson.loads, 'f')
        raises(ValueError, _pypyjson.loads, 'falXX')
        

    def test_decode_string(self):
        import _pypyjson
        res = _pypyjson.loads('"hello"')
        assert res == u'hello'
        assert type(res) is unicode

    def test_decode_string_utf8(self):
        import _pypyjson
        s = u'àèìòù'
        res = _pypyjson.loads('"%s"' % s.encode('utf-8'))
        assert res == s

    def test_skip_whitespace(self):
        import _pypyjson
        s = '   "hello"   '
        assert _pypyjson.loads(s) == u'hello'
        s = '   "hello"   extra'
        raises(ValueError, "_pypyjson.loads(s)")

    def test_unterminated_string(self):
        import _pypyjson
        s = '"hello' # missing the trailing "
        raises(ValueError, "_pypyjson.loads(s)")

    def test_escape_sequence(self):
        import _pypyjson
        assert _pypyjson.loads(r'"\\"') == u'\\'
        assert _pypyjson.loads(r'"\""') == u'"'
        assert _pypyjson.loads(r'"\/"') == u'/'       
        assert _pypyjson.loads(r'"\b"') == u'\b'
        assert _pypyjson.loads(r'"\f"') == u'\f'
        assert _pypyjson.loads(r'"\n"') == u'\n'
        assert _pypyjson.loads(r'"\r"') == u'\r'
        assert _pypyjson.loads(r'"\t"') == u'\t'

    def test_escape_sequence_in_the_middle(self):
        import _pypyjson
        s = r'"hello\nworld"'
        assert _pypyjson.loads(s) == "hello\nworld"

    def test_unterminated_string_after_escape_sequence(self):
        import _pypyjson
        s = r'"hello\nworld' # missing the trailing "
        raises(ValueError, "_pypyjson.loads(s)")
        
    def test_escape_sequence_unicode(self):
        import _pypyjson
        s = r'"\u1234"'
        assert _pypyjson.loads(s) == u'\u1234'

    def test_invalid_utf_8(self):
        import _pypyjson
        s = '"\xe0"' # this is an invalid UTF8 sequence inside a string
        raises(UnicodeDecodeError, "_pypyjson.loads(s)")

    def test_decode_numeric(self):
        import sys
        import _pypyjson
        def check(s, val):
            res = _pypyjson.loads(s)
            assert type(res) is type(val)
            assert res == val
        #
        check('42', 42)
        check('-42', -42)
        check('42.123', 42.123)
        check('42E0', 42.0)
        check('42E3', 42000.0)
        check('42E-1', 4.2)
        check('42E+1', 420.0)
        check('42.123E3', 42123.0)
        check('0', 0)
        check('-0', 0)
        check('0.123', 0.123)
        check('0E3', 0.0)
        check('5E0001', 50.0)
        check(str(1 << 32), 1 << 32)
        check(str(1 << 64), 1 << 64)
        #
        x = str(sys.maxint+1) + '.123'
        check(x, float(x))
        x = str(sys.maxint+1) + 'E1'
        check(x, float(x))
        x = str(sys.maxint+1) + 'E-1'
        check(x, float(x))
        #
        check('1E400', float('inf'))
        ## # these are non-standard but supported by CPython json
        check('Infinity', float('inf'))
        check('-Infinity', float('-inf'))

    def test_nan(self):
        import math
        import _pypyjson
        res = _pypyjson.loads('NaN')
        assert math.isnan(res)

    def test_decode_numeric_invalid(self):
        import _pypyjson
        def error(s):
            raises(ValueError, _pypyjson.loads, s)
        #
        error('  42   abc')
        error('.123')
        error('+123')
        error('12.')
        error('12.-3')
        error('12E')
        error('12E-')
        error('0123') # numbers can't start with 0

    def test_decode_object(self):
        import _pypyjson
        assert _pypyjson.loads('{}') == {}
        assert _pypyjson.loads('{  }') == {}
        #
        s = '{"hello": "world", "aaa": "bbb"}'
        assert _pypyjson.loads(s) == {'hello': 'world',
                                      'aaa': 'bbb'}
        raises(ValueError, _pypyjson.loads, '{"key"')
        raises(ValueError, _pypyjson.loads, '{"key": 42')

    def test_decode_object_nonstring_key(self):
        import _pypyjson
        raises(ValueError, "_pypyjson.loads('{42: 43}')")
        
    def test_decode_array(self):
        import _pypyjson
        assert _pypyjson.loads('[]') == []
        assert _pypyjson.loads('[  ]') == []
        assert _pypyjson.loads('[1]') == [1]
        assert _pypyjson.loads('[1, 2]') == [1, 2]
        raises(ValueError, "_pypyjson.loads('[1: 2]')")
        raises(ValueError, "_pypyjson.loads('[1, 2')")
        raises(ValueError, """_pypyjson.loads('["extra comma",]')""")

    def test_unicode_surrogate_pair(self):
        import _pypyjson
        expected = u'z\U0001d120x'
        res = _pypyjson.loads('"z\\ud834\\udd20x"')
        assert res == expected

    def test_surrogate_pair(self):
        import _pypyjson
        json = '{"a":"\\uD83D"}'
        res = _pypyjson.loads(json)
        assert res == {u'a': u'\ud83d'}

    def test_cache_keys(self):
        import _pypyjson
        json = '[{"a": 1}, {"a": 2}]'
        res = _pypyjson.loads(json)
        assert res == [{u'a': 1}, {u'a': 2}]

    def test_tab_in_string_should_fail(self):
        import _pypyjson
        # http://json.org/JSON_checker/test/fail25.json
        s = '["\ttab\tcharacter\tin\tstring\t"]'
        raises(ValueError, "_pypyjson.loads(s)")

    def test_raw_encode_basestring_ascii(self):
        import _pypyjson
        def check(s):
            s = _pypyjson.raw_encode_basestring_ascii(s)
            assert type(s) is str
            return s
        assert check("") == ""
        assert check(u"") == ""
        assert check("abc ") == "abc "
        assert check(u"abc ") == "abc "
        raises(UnicodeDecodeError, check, "\xc0")
        assert check("\xc2\x84") == "\\u0084"
        assert check("\xf0\x92\x8d\x85") == "\\ud808\\udf45"
        assert check(u"\ud808\udf45") == "\\ud808\\udf45"
        assert check(u"\U00012345") == "\\ud808\\udf45"
        assert check("a\"c") == "a\\\"c"
        assert check("\\\"\b\f\n\r\t") == '\\\\\\"\\b\\f\\n\\r\\t'
        assert check("\x07") == "\\u0007"

    def test_error_position(self):
        import _pypyjson
        test_cases = [
            ('[,', "No JSON object could be decoded: unexpected ',' at char 1"),
            ('{"spam":[}', "No JSON object could be decoded: unexpected '}' at char 9"),
            ('[42:', "Unexpected ':' when decoding array (char 3)"),
            ('[42 "spam"', "Unexpected '\"' when decoding array (char 4)"),
            ('[42,]', "No JSON object could be decoded: unexpected ']' at char 4"),
            ('{"spam":[42}', "Unexpected '}' when decoding array (char 11)"),
            ('["]', 'Unterminated string starting at char 1'),
            ('["spam":', "Unexpected ':' when decoding array (char 7)"),
            ('[{]', "Key name must be string at char 2"),
        ]
        for inputtext, errmsg in test_cases:
            exc = raises(ValueError, _pypyjson.loads, inputtext)
            assert str(exc.value) == errmsg
