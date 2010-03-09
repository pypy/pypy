

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
        d = {}
        assert 'a%b' == 'a%%b' % d

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
        d = {}
        assert '' % d == ''
        n = 5
        raises(TypeError, "'' % n")
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
        n = 23
        assert 'a23b' == 'a%sb' % n
        assert '23b' == '%sb' % n
        assert 'a23' == 'a%s' % n
        assert '23' == '%s' % n

    def test_format_percent(self):
        t = ()
        assert 'a%b' == 'a%%b' % t
        assert '%b' == '%%b' % t
        assert 'a%' == 'a%%' % t
        assert '%' == '%%' % t

    def test_format_too_much(self):
        raises(TypeError, '%s%s'.__mod__, ())
        raises(TypeError, '%s%s'.__mod__, (23,))

    def test_format_not_enough(self):
        raises(TypeError, '%s%s'.__mod__, (23,)*3)
        raises(TypeError, '%s%s'.__mod__, (23,)*4)

    def test_format_string(self):
        s = '23'
        assert '23' == '%s' % s
        assert "'23'" == '%r' % s
        raises(TypeError, '%d'.__mod__, s)

    def test_format_float(self):
        f = 23.456
        assert '23' == '%d' % f
        assert '17' == '%x' % f
        assert '23.456' == '%s' % f
        # for 'r' use a float that has an exact decimal rep:
        g = 23.125
        assert '23.125' == '%r' % g
        h = 0.0276
        assert '0.028' == '%.3f' % h    # should work on most platforms...
        big = 1E200
        assert '   inf' == '%6g' % (big * big)

    def test_format_int(self):
        import sys
        n = 23
        z = 0
        assert '23' == '%d' % n
        assert '17' == '%x' % n
        assert '0x17' == '%#x' % n
        assert '0x0' == '%#x' % z
        assert '23' == '%s' % n
        assert '23' == '%r' % n
        assert ('%d' % (-sys.maxint-1,) == '-' + str(sys.maxint+1)
                                        == '-%d' % (sys.maxint+1,))
        n = 28
        m = 8
        assert '1C' == '%X' % n
        assert '0X1C' == '%#X' % n
        assert '10' == '%o' % m
        assert '010' == '%#o' % m
        assert '-010' == '%#o' % -m
        assert '0' == '%o' % z
        assert '0' == '%#o' % z

        n = 23
        f = 5
        assert '-0x017' == '%#06x' % -n
        assert '' == '%.0o' % z
        assert '0' == '%#.0o' % z
        assert '5' == '%.0o' % f
        assert '05' == '%#.0o' % f
        assert '000' == '%.3o' % z
        assert '000' == '%#.3o' % z
        assert '005' == '%.3o' % f
        assert '005' == '%#.3o' % f
        assert '27' == '%.2o' % n
        assert '027' == '%#.2o' % n

    def test_format_list(self):
        l = [1,2]
        assert '<[1, 2]>' == '<%s>' % l
        assert '<[1, 2]-[3, 4]>' == '<%s-%s>' % (l, [3,4])

    def test_format_tuple(self):
        t = (1,2)
        assert '<(1, 2)>' == '<%s>' % (t,)
        assert '<(1, 2)-(3, 4)>' == '<%s-%s>' % (t, (3,4))

    def test_format_dict(self):

        # I'll just note that the first of these two completely
        # contradicts what CPython's documentation says:

        #     When the right argument is a dictionary (or other
        #     mapping type), then the formats in the string
        #     \emph{must} include a parenthesised mapping key into
        #     that dictionary inserted immediately after the
        #     \character{\%} character.

        # It is what CPython *does*, however.  All software sucks.

        d = {1:2}
        assert '<{1: 2}>' == '<%s>' % d
        assert '<{1: 2}-{3: 4}>' == '<%s-%s>' % (d, {3:4})

    def test_format_wrong_char(self):
        raises(ValueError, 'a%Zb'.__mod__, ((23,),))

    def test_incomplete_format(self):
        raises(ValueError, '%'.__mod__, ((23,),))
        raises(ValueError, '%('.__mod__, ({},))

    def test_format_char(self):
        import sys
        A = 65
        e = 'e'
        assert '%c' % A == 'A'
        assert '%c' % e == 'e'
        raises(OverflowError, '%c'.__mod__, (256,))
        raises(OverflowError, '%c'.__mod__, (-1,))
        raises(OverflowError, u'%c'.__mod__, (sys.maxunicode+1,))
        raises(TypeError, '%c'.__mod__, ("bla",))
        raises(TypeError, '%c'.__mod__, ("",))
        raises(TypeError, '%c'.__mod__, (['c'],))

class AppTestWidthPrec:
    def test_width(self):
        a = 'a'
        assert "%3s" % a == '  a'
        assert "%-3s"% a == 'a  '

    def test_prec_cornercase(self):
        z = 0
        assert "%.0x" % z == ''
        assert "%.x" % z == ''
        assert "%.0d" % z == ''
        assert "%.i" % z == ''
        assert "%.0o" % z == ''
        assert "%.o" % z == ''

    def test_prec_string(self):
        a = 'a'
        abcde = 'abcde'
        assert "%.3s"% a ==     'a'
        assert "%.3s"% abcde == 'abc'

    def test_prec_width_string(self):
        a = 'a'
        abcde = 'abcde'
        assert "%5.3s" % a ==     '    a'
        assert "%5.3s" % abcde == '  abc'
        assert "%-5.3s"% a ==     'a    '
        assert "%-5.3s"% abcde == 'abc  '

    def test_zero_pad(self):
        one = 1
        ttf = 2.25
        assert "%02d" % one ==   "01"
        assert "%05d" % one ==   "00001"
        assert "%-05d" % one ==  "1    "
        assert "%04f" % ttf == "2.250000"
        assert "%05g" % ttf == "02.25"
        assert "%-05g" % ttf =="2.25 "
        assert "%05s" % ttf == " 2.25"

        
    def test_star_width(self):
        f = 5
        assert "%*s" %( f, 'abc') ==  '  abc'
        assert "%*s" %(-f, 'abc') ==  'abc  '
        assert "%-*s"%( f, 'abc') ==  'abc  '
        assert "%-*s"%(-f, 'abc') ==  'abc  '

    def test_star_prec(self):
        t = 3
        assert "%.*s"%( t, 'abc') ==  'abc'
        assert "%.*s"%( t, 'abcde') ==  'abc'
        assert "%.*s"%(-t, 'abc') ==  ''

    def test_star_width_prec(self):
        f = 5
        assert "%*.*s"%( f, 3, 'abc') ==    '  abc'
        assert "%*.*s"%( f, 3, 'abcde') ==  '  abc'
        assert "%*.*s"%(-f, 3, 'abcde') ==  'abc  '

    def test_too_long(self):
        def f(fmt, x):
            return fmt % x
        raises(OverflowError, f, "%.70f", 2.0)
        raises(OverflowError, f, "%.110g", 2.0)

    def test_subnormal(self):
        inf = 1e300 * 1e300
        assert "%f" % (inf,) == 'inf'
        assert "%f" % (-inf,) == '-inf'
        nan = inf / inf
        assert "%f" % (nan,) == 'nan'
        assert "%f" % (-nan,) == 'nan'

class AppTestUnicodeObject:
    def test_unicode_convert(self):
        u = u"x"
        assert isinstance("%s" % u, unicode)

    def test_unicode_nonascii(self):
        """
        Interpolating a unicode string with non-ascii characters in it into
        a string format should decode the format string as ascii and return
        unicode.
        """
        u = u'\x80'
        result = "%s" % u
        assert isinstance(result, unicode)
        assert result == u

    def test_unicode_d(self):
        t = 3
        assert u"%.1d" % t == '3'

    def test_unicode_overflow(self):
        skip("nicely passes on top of CPython but requires > 2GB of RAM")
        import sys
        raises((OverflowError, MemoryError), 'u"%.*d" % (sys.maxint, 1)')

    def test_unicode_format_a(self):
        ten = 10L
        assert u'%x' % ten == 'a'

    def test_long_no_overflow(self):
        big = 100000000000L
        assert "%x" % big == "174876e800"

    def test_missing_cases(self):
        big = -123456789012345678901234567890L
        print '%032d' % big
        assert '%032d' % big == '-0123456789012345678901234567890'

    def test_invalid_char(self):
        f = 4
        raises(ValueError, 'u"%\u1234" % (f,)')
