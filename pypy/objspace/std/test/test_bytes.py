
class AppTestBytesArray:
    def test_basics(self):
        b = bytearray()
        assert type(b) is bytearray
        assert b.__class__ is bytearray

    def test_len(self):
        b = bytearray('test')
        assert len(b) == 4

    def test_nohash(self):
        raises(TypeError, hash, bytearray())

    def test_repr(self):
        assert repr(bytearray()) == "bytearray(b'')"
        assert repr(bytearray('test')) == "bytearray(b'test')"
        assert repr(bytearray("d'oh")) == r"bytearray(b'd\'oh')"

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

    def test_contains(self):
        assert ord('l') in bytearray('hello')

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

        assert bytearray('hello').count('l') == 2
        assert bytearray('hello').count(bytearray('l')) == 2
        assert bytearray('hello').count(ord('l')) == 2

        assert bytearray('hello').index('e') == 1
        assert bytearray('hello').count(bytearray('e')) == 1
        assert bytearray('hello').index(ord('e')) == 1

        r = bytearray('1').zfill(5)
        assert type(r) is bytearray and r == '00001'
        r = bytearray('1\t2').expandtabs(5)
        assert type(r) is bytearray and r == '1    2'


