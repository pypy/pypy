

class AppTestStringObjectWithDict:

    def test_format_item(self):
        d = {'i': 23}
        assert 'a23b' == 'a%(i)sb' % d
        assert '23b' == '%(i)sb' % d
        assert 'a23' == 'a%(i)s' % d
        assert '23' == '%(i)s' % d

    def test_format_two_items(self):
        d = {'i': 23, 'j': 42}
        assert 'a23b42c' == 'a%(i)sb%(j)sc' % d
        assert 'a23b23c' == 'a%(i)sb%(i)sc' % d

    def test_format_percent(self):
        assert 'a%b' == 'a%%b' % {} 

    def test_format_empty_key(self):
        d = {'':42}
        assert '42' == '%()s' % d

    def test_format_wrong_char(self):
        d = {'i': 23}
        raises(ValueError, 'a%(i)Zb'.__mod__, d) 

    def test_format_missing(self):
        d = {'i': 23}
        raises(KeyError, 'a%(x)sb'.__mod__, d) 

    def test_format_error(self):
        assert '' % {} == ''
        raises(TypeError, "'' % 5")
        class MyMapping(object):
            def __getitem__(self, key):
                py.test.fail('should not be here')
        assert '' % MyMapping() == ''
        class MyMapping2(object):
            def __getitem__(self, key):
                return key
        assert '%(key)s'%MyMapping2() == 'key'
        assert u'%(key)s'%MyMapping2() == u'key'

class AppTestStringObject:

    def test_format_item(self):
        assert 'a23b' == 'a%sb' % 23
        assert '23b' == '%sb' % 23
        assert 'a23' == 'a%s' % 23
        assert '23' == '%s' % 23

    def test_format_percent(self):
        assert 'a%b' == 'a%%b' % ()
        assert '%b' == '%%b' % ()
        assert 'a%' == 'a%%' % ()
        assert '%' == '%%' % ()

    def test_format_too_much(self):
        raises(TypeError, '%s%s'.__mod__, ())
        raises(TypeError, '%s%s'.__mod__, (23,))

    def test_format_not_enough(self):
        raises(TypeError, '%s%s'.__mod__, (23,)*3)
        raises(TypeError, '%s%s'.__mod__, (23,)*4)

    def test_format_string(self):
        assert '23' == '%s' % '23'
        assert "'23'" == '%r' % '23'
        raises(TypeError, '%d'.__mod__, "23")

    def test_format_float(self):
        assert '23' == '%d' % 23.456
        assert '17' == '%x' % 23.456
        assert '23.456' == '%s' % 23.456
        # for 'r' use a float that has an exact decimal rep:
        assert '23.125' == '%r' % 23.125
        assert '0.028' == '%.3f' % 0.0276    # should work on most platforms...
        assert '   inf' == '%6g' % (1E200 * 1E200)

    def test_format_int(self):
        import sys
        assert '23' == '%d' % 23
        assert '17' == '%x' % 23
        assert '0x17' == '%#x' % 23
        assert '0x0' == '%#x' % 0
        assert '23' == '%s' % 23
        assert '23' == '%r' % 23
        assert ('%d' % (-sys.maxint-1,) == '-' + str(sys.maxint+1)
                                        == '-%d' % (sys.maxint+1,))
        assert '1C' == '%X' % 28
        assert '0X1C' == '%#X' % 28
        assert '10' == '%o' % 8
        assert '010' == '%#o' % 8
        assert '-010' == '%#o' % -8
        assert '0' == '%o' % 0
        assert '0' == '%#o' % 0

        assert '-0x017' == '%#06x' % -23
        assert '0' == '%#.0o' % 0

    def test_format_list(self):
        assert '<[1, 2]>' == '<%s>' % [1,2]
        assert '<[1, 2]-[3, 4]>' == '<%s-%s>' % ([1,2], [3,4])

    def test_format_tuple(self):
        assert '<(1, 2)>' == '<%s>' % ((1,2),)
        assert '<(1, 2)-(3, 4)>' == '<%s-%s>' % ((1,2), (3,4))

    def test_format_dict(self):

        # I'll just note that the first of these two completely
        # contradicts what CPython's documentation says:

        #     When the right argument is a dictionary (or other
        #     mapping type), then the formats in the string
        #     \emph{must} include a parenthesised mapping key into
        #     that dictionary inserted immediately after the
        #     \character{\%} character.

        # It is what CPython *does*, however.  All software sucks.
        
        assert '<{1: 2}>' == '<%s>' % {1:2}
        assert '<{1: 2}-{3: 4}>' == '<%s-%s>' % ({1:2}, {3:4})

    def test_format_wrong_char(self):
        raises(ValueError, 'a%Zb'.__mod__, ((23,),))

    def test_incomplete_format(self):
        raises(ValueError, '%'.__mod__, ((23,),))
        raises(ValueError, '%('.__mod__, ({},))

    def test_format_char(self):
        import sys
        assert '%c' % 65 == 'A'
        assert '%c' % 'e' == 'e'
        raises(OverflowError, '%c'.__mod__, (256,))
        raises(OverflowError, '%c'.__mod__, (-1,))
        raises(OverflowError, u'%c'.__mod__, (sys.maxunicode+1,))
        raises(TypeError, '%c'.__mod__, ("bla",))
        raises(TypeError, '%c'.__mod__, ("",))
        raises(TypeError, '%c'.__mod__, (['c'],))

class AppTestWidthPrec:
    def test_width(self):
        assert "%3s" %'a' == '  a'
        assert "%-3s"%'a' == 'a  '

    def test_prec_cornercase(self):
        assert "%.0x" % 0 == ''
        assert "%.x" % 0 == ''
        assert "%.0d" % 0 == ''
        assert "%.i" % 0 == ''
        assert "%.0o" % 0 == ''
        assert "%.o" % 0 == ''

    def test_prec_string(self):
        assert "%.3s"%'a' ==     'a'
        assert "%.3s"%'abcde' == 'abc'

    def test_prec_width_string(self):
        assert "%5.3s" %'a' ==     '    a'
        assert "%5.3s" %'abcde' == '  abc'
        assert "%-5.3s"%'a' ==     'a    '
        assert "%-5.3s"%'abcde' == 'abc  '

    def test_zero_pad(self):
        assert "%02d"%1 ==   "01"
        assert "%05d"%1 ==   "00001"
        assert "%-05d"%1 ==  "1    "
        assert "%04f"%2.25 == "2.250000"
        assert "%05g"%2.25 == "02.25"
        assert "%-05g"%2.25 =="2.25 "
        assert "%05s"%2.25 == " 2.25"

        
    def test_star_width(self):
        assert "%*s" %( 5, 'abc') ==  '  abc'
        assert "%*s" %(-5, 'abc') ==  'abc  '
        assert "%-*s"%( 5, 'abc') ==  'abc  '
        assert "%-*s"%(-5, 'abc') ==  'abc  '

    def test_star_prec(self):
        assert "%.*s"%( 3, 'abc') ==  'abc'
        assert "%.*s"%( 3, 'abcde') ==  'abc'
        assert "%.*s"%(-3, 'abc') ==  ''

    def test_star_width_prec(self):
        assert "%*.*s"%( 5, 3, 'abc') ==    '  abc'
        assert "%*.*s"%( 5, 3, 'abcde') ==  '  abc'
        assert "%*.*s"%(-5, 3, 'abcde') ==  'abc  '

    def test_too_long(self):
        def f(fmt, x):
            return fmt % x
        raises(OverflowError, f, "%.70f", 2.0)
        raises(OverflowError, f, "%.110g", 2.0)

class AppTestUnicodeObject:
    def test_unicode_convert(self):
        assert isinstance("%s" % (u"x"), unicode)

    def test_unicode_nonascii(self):
        """
        Interpolating a unicode string with non-ascii characters in it into
        a string format should decode the format string as ascii and return
        unicode.
        """
        result = "%s" % u'\x80'
        assert isinstance(result, unicode)
        assert result == u'\x80'

    def test_unicode_d(self):
        assert u"%.1d" % 3 == '3'

    def test_unicode_overflow(self):
        skip("nicely passes on top of CPython but requires > 2GB of RAM")
        import sys
        raises((OverflowError, MemoryError), 'u"%.*d" % (sys.maxint, 1)')

    def test_unicode_format_a(self):
        assert u'%x' % 10L == 'a'

    def test_long_no_overflow(self):
        assert "%x" % 100000000000L == "174876e800"

    def test_missing_cases(self):
        print '%032d' % -123456789012345678901234567890L
        assert '%032d' % -123456789012345678901234567890L == '-0123456789012345678901234567890'

    def test_invalid_char(self):
        raises(ValueError, 'u"%\u1234" % (4,)')
