import autopath

objspacename = 'std'

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

    def test_format_int(self):
        assert '23' == '%d' % 23
        assert '17' == '%x' % 23
        assert '0x17' == '%#x' % 23
        assert '23' == '%s' % 23
        assert '23' == '%r' % 23

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

class AppTestWidthPrec:
    def test_width(self):
        assert "%3s" %'a' == '  a'
        assert "%-3s"%'a' == 'a  '

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
