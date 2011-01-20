
class AppTestBytesArray:
    def test_basics(self):
        b = bytearray()
        assert type(b) is bytearray
        assert b.__class__ is bytearray

    def test_constructor(self):
        assert bytearray() == ""
        assert bytearray('abc') == "abc"
        assert bytearray(['a', 'b', 'c']) == "abc"
        assert bytearray([65, 66, 67]) == "ABC"
        assert bytearray(5) == '\0' * 5
        raises(ValueError, bytearray, ['a', 'bc'])
        raises(ValueError, bytearray, [65, -3])
        raises(TypeError, bytearray, [65.0])

    def test_init_override(self):
        class subclass(bytearray):
            def __init__(self, newarg=1, *args, **kwargs):
                bytearray.__init__(self, *args, **kwargs)
        x = subclass(4, source="abcd")
        assert x == "abcd"

    def test_encoding(self):
        data = u"Hello world\n\u1234\u5678\u9abc\def0\def0"
        for encoding in 'utf8', 'utf16':
            b = bytearray(data, encoding)
            assert b == data.encode(encoding)
        raises(TypeError, bytearray, 9, 'utf8')

    def test_encoding_with_ignore_errors(self):
        data = u"H\u1234"
        b = bytearray(data, "latin1", errors="ignore")
        assert b == "H"

    def test_len(self):
        b = bytearray('test')
        assert len(b) == 4

    def test_nohash(self):
        raises(TypeError, hash, bytearray())

    def test_repr(self):
        assert repr(bytearray()) == "bytearray(b'')"
        assert repr(bytearray('test')) == "bytearray(b'test')"
        assert repr(bytearray("d'oh")) == r"bytearray(b'd\'oh')"

    def test_str(self):
        assert str(bytearray()) == ""
        assert str(bytearray('test')) == "test"
        assert str(bytearray("d'oh")) == "d'oh"

    def test_getitem(self):
        b = bytearray('test')
        assert b[0] == ord('t')
        assert b[2] == ord('s')
        raises(IndexError, b.__getitem__, 4)
        assert b[1:5] == bytearray('est')
        assert b[slice(1,5)] == bytearray('est')

    def test_arithmetic(self):
        b1 = bytearray('hello ')
        b2 = bytearray('world')
        assert b1 + b2 == bytearray('hello world')
        assert b1 * 2 == bytearray('hello hello ')
        assert b1 * 1 is not b1

    def test_contains(self):
        assert ord('l') in bytearray('hello')
        assert 'l' in bytearray('hello')

    def test_translate(self):
        b = 'hello'
        ba = bytearray(b)
        rosetta = bytearray(range(0, 256))
        rosetta[ord('o')] = ord('e')

        for table in rosetta, str(rosetta):
            c = ba.translate(table)
            assert ba == bytearray('hello')
            assert c == bytearray('helle')

            c = ba.translate(rosetta, 'l')
            assert c == bytearray('hee')
            assert isinstance(c, bytearray)

    def test_strip(self):
        b = bytearray('mississippi ')

        assert b.strip() == 'mississippi'
        assert b.strip(None) == 'mississippi'

        b = bytearray('mississippi')

        for strip_type in str, memoryview:
            assert b.strip(strip_type('i')) == 'mississipp'
            assert b.strip(strip_type('m')) == 'ississippi'
            assert b.strip(strip_type('pi')) == 'mississ'
            assert b.strip(strip_type('im')) == 'ssissipp'
            assert b.strip(strip_type('pim')) == 'ssiss'
            assert b.strip(strip_type(b)) == ''

    def test_iter(self):
        assert list(bytearray('hello')) == [104, 101, 108, 108, 111]

    def test_compare(self):
        assert bytearray('hello') == bytearray('hello')
        assert bytearray('hello') < bytearray('world')
        assert bytearray('world') > bytearray('hello')

    def test_compare_str(self):
        assert bytearray('hello1') == 'hello1'
        assert not (bytearray('hello1') != 'hello1')
        assert 'hello2' == bytearray('hello2')
        assert not ('hello1' != bytearray('hello1'))
        # unicode is always different
        assert not (bytearray('hello3') == unicode('world'))
        assert bytearray('hello3') != unicode('hello3')
        assert unicode('hello3') != bytearray('world')
        assert unicode('hello4') != bytearray('hello4')
        assert not (bytearray('') == u'')
        assert not (u'' == bytearray(''))
        assert bytearray('') != u''
        assert u'' != bytearray('')

    def test_stringlike_operations(self):
        assert bytearray('hello').islower()
        assert bytearray('HELLO').isupper()
        assert bytearray('hello').isalpha()
        assert not bytearray('hello2').isalpha()
        assert bytearray('hello2').isalnum()
        assert bytearray('1234').isdigit()
        assert bytearray('   ').isspace()
        assert bytearray('Abc').istitle()

        assert bytearray('hello').count('l') == 2
        assert bytearray('hello').count(bytearray('l')) == 2
        assert bytearray('hello').count(ord('l')) == 2

        assert bytearray('hello').index('e') == 1
        assert bytearray('hello').rindex('l') == 3
        assert bytearray('hello').index(bytearray('e')) == 1
        assert bytearray('hello').index(ord('e')) == 1
        assert bytearray('hello').find('l') == 2
        assert bytearray('hello').rfind('l') == 3

        assert bytearray('hello').startswith('he')
        assert bytearray('hello').startswith(bytearray('he'))
        assert bytearray('hello').endswith('lo')
        assert bytearray('hello').endswith(bytearray('lo'))

    def test_stringlike_conversions(self):
        # methods that should return bytearray (and not str)
        def check(result, expected):
            assert result == expected
            assert type(result) is bytearray

        check(bytearray('abc').replace('b', bytearray('d')), 'adc')

        check(bytearray('abc').upper(), 'ABC')
        check(bytearray('ABC').lower(), 'abc')
        check(bytearray('abc').title(), 'Abc')
        check(bytearray('AbC').swapcase(), 'aBc')
        check(bytearray('abC').capitalize(), 'Abc')

        check(bytearray('abc').ljust(5),  'abc  ')
        check(bytearray('abc').rjust(5),  '  abc')
        check(bytearray('abc').center(5), ' abc ')
        check(bytearray('1').zfill(5), '00001')
        check(bytearray('1\t2').expandtabs(5), '1    2')

        check(bytearray(',').join(['a', bytearray('b')]), 'a,b')
        check(bytearray('abca').lstrip('a'), 'bca')
        check(bytearray('cabc').rstrip('c'), 'cab')
        check(bytearray('abc').lstrip(memoryview('a')), 'bc')
        check(bytearray('abc').rstrip(memoryview('c')), 'ab')
        check(bytearray('aba').strip('a'), 'b')

    def test_split(self):
        # methods that should return a sequence of bytearrays
        def check(result, expected):
            assert result == expected
            assert set(type(x) for x in result) == set([bytearray])

        b = bytearray('mississippi')
        check(b.split('i'), eval("[b'm', b'ss', b'ss', b'pp', b'']"))
        check(b.rsplit('i'), eval("[b'm', b'ss', b'ss', b'pp', b'']"))
        check(b.rsplit('i', 2), eval("[b'mississ', b'pp', b'']"))

        check(b.partition(eval("b'ss'")), eval("(b'mi', b'ss', b'issippi')"))
        check(b.rpartition(eval("b'ss'")), eval("(b'missi', b'ss', b'ippi')"))

    def test_append(self):
        b = bytearray('abc')
        b.append('d')
        b.append(ord('e'))
        assert b == 'abcde'

    def test_insert(self):
        b = bytearray('abc')
        b.insert(0, 'd')
        assert b == bytearray('dabc')

        b.insert(-1, ord('e'))
        assert b == bytearray('dabec')

        b.insert(6, 'f')
        assert b == bytearray('dabecf')

        b.insert(1, 'g')
        assert b == bytearray('dgabecf')

        b.insert(-12, 'h')
        assert b == bytearray('hdgabecf')

        raises(ValueError, b.insert, 1, 'go')
        raises(TypeError, b.insert, 'g', 'o')

    def test_pop(self):
        b = bytearray('world')
        assert b.pop() == ord('d')
        assert b.pop(0) == ord('w')
        assert b.pop(-2) == ord('r')
        raises(IndexError, b.pop, 10)
        raises(OverflowError, bytearray().pop)
        assert bytearray(b'\xff').pop() == 0xff

    def test_remove(self):
        class Indexable:
            def __index__(self):
                return ord('e')

        b = bytearray(b'hello')
        b.remove(ord('l'))
        assert b == 'helo'
        b.remove(ord('l'))
        assert b == 'heo'
        raises(ValueError, b.remove, ord('l'))
        raises(ValueError, b.remove, 400)
        raises(TypeError, b.remove, u'e')
        raises(TypeError, b.remove, 2.3)
        # remove first and last
        b.remove(ord('o'))
        b.remove(ord('h'))
        assert b == 'e'
        raises(TypeError, b.remove, u'e')
        b.remove(Indexable())
        assert b == ''

    def test_reverse(self):
        b = bytearray('hello')
        b.reverse()
        assert b == bytearray('olleh')

    def test_delitem(self):
        b = bytearray('abc')
        del b[1]
        assert b == bytearray('ac')
        del b[1:1]
        assert b == bytearray('ac')
        del b[:]
        assert b == bytearray()

        b = bytearray('fooble')
        del b[::2]
        assert b == bytearray('obe')

    def test_iadd(self):
        b = bytearray('abc')
        b += 'def'
        assert b == 'abcdef'
        assert isinstance(b, bytearray)

    def test_fromhex(self):
        raises(TypeError, bytearray.fromhex, 9)

        assert bytearray.fromhex('') == bytearray()
        assert bytearray.fromhex(u'') == bytearray()

        b = bytearray([0x1a, 0x2b, 0x30])
        assert bytearray.fromhex('1a2B30') == b
        assert bytearray.fromhex(u'1a2B30') == b
        assert bytearray.fromhex(u'  1A 2B  30   ') == b
        assert bytearray.fromhex(u'0000') == '\0\0'

        raises(ValueError, bytearray.fromhex, u'a')
        raises(ValueError, bytearray.fromhex, u'A')
        raises(ValueError, bytearray.fromhex, u'rt')
        raises(ValueError, bytearray.fromhex, u'1a b cd')
        raises(ValueError, bytearray.fromhex, u'\x00')
        raises(ValueError, bytearray.fromhex, u'12   \x00   34')
        raises(UnicodeEncodeError, bytearray.fromhex, u'\u1234')

    def test_extend(self):
        b = bytearray('abc')
        b.extend(bytearray('def'))
        b.extend('ghi')
        assert b == 'abcdefghi'
        b.extend(buffer('jkl'))
        assert b == 'abcdefghijkl'

        b = bytearray('world')
        b.extend([ord(c) for c in 'hello'])
        assert b == bytearray('worldhello')

        b = bytearray('world')
        b.extend(list('hello'))
        assert b == bytearray('worldhello')

        b = bytearray('world')
        b.extend(c for c in 'hello')
        assert b == bytearray('worldhello')

        raises(ValueError, b.extend, ['fish'])
        raises(ValueError, b.extend, [256])
        raises(TypeError, b.extend, object())
        raises(TypeError, b.extend, [object()])
        raises(TypeError, b.extend, u"unicode")

    def test_setslice(self):
        b = bytearray('hello')
        b[:] = [ord(c) for c in 'world']
        assert b == bytearray('world')

        b = bytearray('hello world')
        b[::2] = 'bogoff'
        assert b == bytearray('beolg ooflf')

        def set_wrong_size():
            b[::2] = 'foo'
        raises(ValueError, set_wrong_size)

    def test_delitem_slice(self):
        b = bytearray('abcdefghi')
        del b[5:8]
        assert b == 'abcdei'
        del b[:3]
        assert b == 'dei'

        b = bytearray('hello world')
        del b[::2]
        assert b == bytearray('el ol')

    def test_setitem(self):
        b = bytearray('abcdefghi')
        b[1] = 'B'
        assert b == 'aBcdefghi'

    def test_setitem_slice(self):
        b = bytearray('abcdefghi')
        b[0:3] = 'ABC'
        assert b == 'ABCdefghi'
        b[3:3] = '...'
        assert b == 'ABC...defghi'
        b[3:6] = '()'
        assert b == 'ABC()defghi'
        b[6:6] = '<<'
        assert b == 'ABC()d<<efghi'

    def test_buffer(self):
        b = bytearray('abcdefghi')
        buf = buffer(b)
        assert buf[2] == 'c'
        buf[3] = 'D'
        assert b == 'abcDefghi'
        buf[4:6] = 'EF'
        assert b == 'abcDEFghi'

    def test_decode(self):
        b = bytearray('abcdefghi')
        u = b.decode('utf-8')
        assert isinstance(u, unicode)
        assert u == u'abcdefghi'

    def test_int(self):
        assert int(bytearray('-1234')) == -1234

    def test_reduce(self):
        assert bytearray('caf\xe9').__reduce__() == (
            bytearray, (u'caf\xe9', 'latin-1'), None)
