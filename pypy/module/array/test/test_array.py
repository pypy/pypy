from pypy.conftest import gettestobjspace
import sys
import py
import py.test


## class AppTestSimpleArray:
##     def setup_class(cls):
##         cls.space = gettestobjspace(usemodules=('array',))
##         cls.w_simple_array = cls.space.appexec([], """():
##             import array
##             return array.simple_array
##         """)

##     def test_simple(self):
##         a = self.simple_array(10)
##         a[5] = 7.42
##         assert a[5] == 7.42


class BaseArrayTests:

    
    def test_ctor(self):
        assert len(self.array('c')) == 0
        assert len(self.array('i')) == 0

        raises(TypeError, self.array, 'hi')
        raises(TypeError, self.array, 1)
        raises(ValueError, self.array, 'q')

        a = self.array('c')
        raises(TypeError, a.append, 7)
        raises(TypeError, a.append, 'hi')
        a.append('h')
        assert a[0] == 'h'
        assert type(a[0]) is str
        assert len(a) == 1

        a = self.array('u')
        raises(TypeError, a.append, 7)
        raises(TypeError, a.append, u'hi')
        a.append(unicode('h'))
        assert a[0] == unicode('h')
        assert type(a[0]) is unicode
        assert len(a) == 1

        a = self.array('c', ('a', 'b', 'c'))
        assert a[0] == 'a'
        assert a[1] == 'b'
        assert a[2] == 'c'
        assert len(a) == 3

        b = self.array('c', a)
        assert len(b) == 3
        assert a == b
        raises(TypeError, self.array, 'i', a)

        a = self.array('i', (1, 2, 3))
        b = self.array('h', (1, 2, 3))
        assert a == b

        for tc in 'bhilBHILfd':
            assert self.array(tc).typecode == tc
            raises(TypeError, self.array, tc, None)

        a = self.array('i', (1, 2, 3))
        b = self.array('h', a)
        assert list(b) == [1, 2, 3]

    def test_value_range(self):
        import sys
        values = (-129, 128, -128, 127, 0, 255, -1, 256,
                  -32768, 32767, -32769, 32768, 65535, 65536,
                  -2147483647, -2147483648, 2147483647, 4294967295, 4294967296,
                  )
        for bb in (8, 16, 32, 64, 128, 256, 512, 1024):
            for b in (bb - 1, bb, bb + 1):
                values += (2 ** b, 2 ** b + 1, 2 ** b - 1,
                           -2 ** b, -2 ** b + 1, -2 ** b - 1)

        for tc, ok, pt in (('b', (  -128,    34,   127),  int),
                           ('B', (     0,    23,   255),  int),
                           ('h', (-32768, 30535, 32767),  int),
                           ('H', (     0, 56783, 65535),  int),
                           ('i', (-32768, 30535, 32767),  int),
                           ('I', (     0, 56783, 65535), long),
                           ('l', (-2 ** 32 / 2, 34, 2 ** 32 / 2 - 1),  int),
                           ('L', (0, 3523532, 2 ** 32 - 1), long),
                           ):
            a = self.array(tc, ok)
            assert len(a) == len(ok)
            for v in ok:
                a.append(v)
            for i, v in enumerate(ok * 2):
                assert a[i] == v
                assert type(a[i]) is pt or (
                    # A special case: we return ints in Array('I') on 64-bits,
                    # whereas CPython returns longs.  The difference is
                    # probably acceptable.
                    tc == 'I' and
                    sys.maxint > 2147483647 and type(a[i]) is int)
            for v in ok:
                a[1] = v
                assert a[0] == ok[0]
                assert a[1] == v
                assert a[2] == ok[2]
            assert len(a) == 2 * len(ok)
            for v in values:
                try:
                    a[1] = v
                    assert a[0] == ok[0]
                    assert a[1] == v
                    assert a[2] == ok[2]
                except OverflowError:
                    pass

        for tc in 'BHIL':
            a = self.array(tc)
            vals = [0, 2 ** a.itemsize - 1]
            a.fromlist(vals)
            assert a.tolist() == vals

            a = self.array(tc.lower())
            vals = [-1 * (2 ** a.itemsize) / 2,  (2 ** a.itemsize) / 2 - 1]
            a.fromlist(vals)
            assert a.tolist() == vals

    def test_float(self):
        values = [0, 1, 2.5, -4.25]
        for tc in 'fd':
            a = self.array(tc, values)
            assert len(a) == len(values)
            for i, v in enumerate(values):
                assert a[i] == v
                assert type(a[i]) is float
            a[1] = 10.125
            assert a[0] == 0
            assert a[1] == 10.125
            assert a[2] == 2.5
            assert len(a) == len(values)

    def test_itemsize(self):
        for t in 'cbB':
            assert(self.array(t).itemsize >= 1)
        for t in 'uhHiI':
            assert(self.array(t).itemsize >= 2)
        for t in 'lLf':
            assert(self.array(t).itemsize >= 4)
        for t in 'd':
            assert(self.array(t).itemsize >= 8)

        inttypes = 'bhil'
        for t in inttypes:
            a = self.array(t, [1, 2, 3])
            b = a.itemsize
            for v in (-2 ** (8 * b) / 2, 2 ** (8 * b) / 2 - 1):
                a[1] = v
                assert a[0] == 1 and a[1] == v and a[2] == 3
            raises(OverflowError, a.append, -2 ** (8 * b) / 2 - 1)
            raises(OverflowError, a.append, 2 ** (8 * b) / 2)

            a = self.array(t.upper(), [1, 2, 3])
            b = a.itemsize
            for v in (0, 2 ** (8 * b) - 1):
                a[1] = v
                assert a[0] == 1 and a[1] == v and a[2] == 3
            raises(OverflowError, a.append, -1)
            raises(OverflowError, a.append, 2 ** (8 * b))

    def test_fromstring(self):
        a = self.array('c')
        a.fromstring('Hi!')
        assert a[0] == 'H' and a[1] == 'i' and a[2] == '!' and len(a) == 3

        for t in 'bBhHiIlLfd':
            a = self.array(t)
            a.fromstring('\x00' * a.itemsize * 2)
            assert len(a) == 2 and a[0] == 0 and a[1] == 0
            if a.itemsize > 1:
                raises(ValueError, a.fromstring, '\x00' * (a.itemsize - 1))
                raises(ValueError, a.fromstring, '\x00' * (a.itemsize + 1))
                raises(ValueError, a.fromstring, '\x00' * (2 * a.itemsize - 1))
                raises(ValueError, a.fromstring, '\x00' * (2 * a.itemsize + 1))
            b = self.array(t, '\x00' * a.itemsize * 2)
            assert len(b) == 2 and b[0] == 0 and b[1] == 0

    def test_fromfile(self):

        ## class myfile(object):
        ##     def __init__(self, c, s):
        ##         self.c = c
        ##         self.s = s
        ##     def read(self,n):
        ##         return self.c*min(n,self.s)
        def myfile(c, s):
            f = open(self.tempfile, 'w')
            f.write(c * s)
            f.close()
            return open(self.tempfile, 'r')

        f = myfile('\x00', 100)
        for t in 'bBhHiIlLfd':
            a = self.array(t)
            a.fromfile(f, 2)
            assert len(a) == 2 and a[0] == 0 and a[1] == 0

        a = self.array('b')
        a.fromfile(myfile('\x01', 20), 2)
        assert len(a) == 2 and a[0] == 1 and a[1] == 1

        a = self.array('h')
        a.fromfile(myfile('\x01', 20), 2)
        assert len(a) == 2 and a[0] == 257 and a[1] == 257

        for i in (0, 1):
            a = self.array('h')
            raises(EOFError, a.fromfile, myfile('\x01', 2 + i), 2)
            assert len(a) == 1 and a[0] == 257

    def test_fromlist(self):
        a = self.array('b')
        raises(OverflowError, a.fromlist, [1, 2, 400])
        assert len(a) == 0

        raises(OverflowError, a.extend, [1, 2, 400])
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        raises(OverflowError, self.array, 'b', [1, 2, 400])

        a = self.array('b', [1, 2])
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        a = self.array('b')
        raises(TypeError, a.fromlist, (1, 2, 400))

        raises(OverflowError, a.extend, (1, 2, 400))
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        raises(TypeError, a.extend, self.array('i', (7, 8)))
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        def gen():
            for i in range(4):
                yield i + 10
        a = self.array('i', gen())
        assert len(a) == 4 and a[2] == 12

        raises(OverflowError, self.array, 'b', (1, 2, 400))

        a = self.array('b', (1, 2))
        assert len(a) == 2 and a[0] == 1 and a[1] == 2

        a.extend(a)
        assert repr(a) == "array('b', [1, 2, 1, 2])"

    def test_fromunicode(self):
        raises(ValueError, self.array('i').fromunicode, unicode('hi'))
        a = self.array('u')
        a.fromunicode(unicode('hi'))
        assert len(a) == 2 and a[0] == 'h' and a[1] == 'i'

        b = self.array('u', unicode('hi'))
        assert len(b) == 2 and b[0] == 'h' and b[1] == 'i'

    def test_sequence(self):
        a = self.array('i', [1, 2, 3, 4])
        assert len(a) == 4
        assert a[0] == 1 and a[1] == 2 and a[2] == 3 and a[3] == 4
        assert a[-4] == 1 and a[-3] == 2 and a[-2] == 3 and a[-1] == 4
        a[-2] = 5
        assert a[0] == 1 and a[1] == 2 and a[2] == 5 and a[3] == 4

        for i in (4, -5):
            raises(IndexError, a.__getitem__, i)

        b = a[0:2]
        assert len(b) == 2 and b[0] == 1 and b[1] == 2
        b[0] = 6
        assert len(b) == 2 and b[0] == 6 and b[1] == 2
        assert a[0] == 1 and a[1] == 2 and a[2] == 5 and a[3] == 4
        assert a.itemsize == b.itemsize

        b = a[0:100]
        assert len(b) == 4
        assert b[0] == 1 and b[1] == 2 and b[2] == 5 and b[3] == 4

        l1 = [2 * i + 1 for i in range(10)]
        a1 = self.array('i', l1)
        for start in range(10):
            for stop in range(start, 10):
                for step in range(1, 10):
                    l2 = l1[start:stop:step]
                    a2 = a1[start:stop:step]
                    assert len(l2) == len(a2)
                    for i in range(len(l2)):
                        assert l2[i] == a2[i]

        a = self.array('i', [1, 2, 3, 4])
        a[1:3] = self.array('i', [5, 6])
        assert len(a) == 4
        assert a[0] == 1 and a[1] == 5 and a[2] == 6 and a[3] == 4
        a[0:-1:2] = self.array('i', [7, 8])
        assert a[0] == 7 and a[1] == 5 and a[2] == 8 and a[3] == 4

        raises(ValueError, "a[1:2:4] = self.array('i', [5, 6, 7])")
        raises(TypeError, "a[1:3] = self.array('I', [5, 6])")
        raises(TypeError, "a[1:3] = [5, 6]")

        a = self.array('i', [1, 2, 3])
        assert a.__getslice__(1, 2) == a[1:2]
        a.__setslice__(1, 2, self.array('i', (7,)))
        assert a[0] == 1 and a[1] == 7 and a[2] == 3

    def test_resizingslice(self):
        a = self.array('i', [1, 2, 3])
        a[1:2] = self.array('i', [7, 8, 9])
        assert repr(a) == "array('i', [1, 7, 8, 9, 3])"
        a[1:2] = self.array('i', [10])
        assert repr(a) == "array('i', [1, 10, 8, 9, 3])"
        a[1:2] = self.array('i')
        assert repr(a) == "array('i', [1, 8, 9, 3])"

        a[1:3] = self.array('i', [11, 12, 13])
        assert repr(a) == "array('i', [1, 11, 12, 13, 3])"
        a[1:3] = self.array('i', [14])
        assert repr(a) == "array('i', [1, 14, 13, 3])"
        a[1:3] = self.array('i')
        assert repr(a) == "array('i', [1, 3])"

        a[1:1] = self.array('i', [15, 16, 17])
        assert repr(a) == "array('i', [1, 15, 16, 17, 3])"
        a[1:1] = self.array('i', [18])
        assert repr(a) == "array('i', [1, 18, 15, 16, 17, 3])"
        a[1:1] = self.array('i')
        assert repr(a) == "array('i', [1, 18, 15, 16, 17, 3])"

        a[:] = self.array('i', [20, 21, 22])
        assert repr(a) == "array('i', [20, 21, 22])"

    def test_reversingslice(self):
        a = self.array('i', [22, 21, 20])
        assert repr(a[::-1]) == "array('i', [20, 21, 22])"
        assert repr(a[2:1:-1]) == "array('i', [20])"
        assert repr(a[2:-1:-1]) == "array('i')"
        assert repr(a[-1:0:-1]) == "array('i', [20, 21])"

        for a in range(-4, 5):
            for b in range(-4, 5):
                for c in [-4, -3, -2, -1, 1, 2, 3, 4]:
                    lst = [1, 2, 3]
                    arr = self.array('i', lst)
                    assert repr(arr[a:b:c]) == \
                           repr(self.array('i', lst[a:b:c]))
                    for vals in ([4, 5], [6], []):
                        try:
                            ok = False
                            lst[a:b:c] = vals
                            ok = True
                            arr[a:b:c] = self.array('i', vals)
                            assert repr(arr) == repr(self.array('i', lst))
                        except ValueError:
                            assert not ok

    def test_reversingslice_pre26(self):
        import sys
        if sys.version_info >= (2, 6):
            skip('arrays can handle more slice ops than lists in 2.6')

        for a in range(-4, 5):
            for b in range(-4, 5):
                for c in [-4, -3, -2, -1, 1, 2, 3, 4]:
                    lst = [1, 2, 3]
                    arr = self.array('i', lst)
                    for vals in ([4, 5], [6], []):
                        try:
                            lst[a:b:c] = vals
                        except ValueError:
                            raises(ValueError,
                                   "arr[a:b:c]=self.array('i', vals)")

    def test_toxxx(self):
        a = self.array('i', [1, 2, 3])
        l = a.tolist()
        assert type(l) is list and len(l) == 3
        assert a[0] == 1 and a[1] == 2 and a[2] == 3

        b = self.array('i', a.tostring())
        assert len(b) == 3 and b[0] == 1 and b[1] == 2 and b[2] == 3

        assert self.array('c', ('h', 'i')).tostring() == 'hi'
        a = self.array('i', [0, 0, 0])
        assert a.tostring() == '\x00' * 3 * a.itemsize

        s = self.array('i', [1, 2, 3]).tostring()
        assert '\x00' in s
        assert '\x01' in s
        assert '\x02' in s
        assert '\x03' in s
        a = self.array('i', s)
        assert a[0] == 1 and a[1] == 2 and a[2] == 3

        from struct import unpack
        values = (-129, 128, -128, 127, 0, 255, -1, 256, -32760, 32760)
        s = self.array('i', values).tostring()
        fmt = 'i' * len(values)
        a = unpack(fmt, s)
        assert a == values

        for tcodes, values in (('bhilfd', (-128, 127, 0, 1, 7, -10)),
                               ('BHILfd', (127, 0, 1, 7, 255, 169)),
                               ('hilHILfd', (32760, 30123, 3422, 23244))):
            for tc in tcodes:
                values += ((2 ** self.array(tc).itemsize) / 2 - 1, )
                s = self.array(tc, values).tostring()
                a = unpack(tc * len(values), s)
                assert a == values

        f = open(self.tempfile, 'w')
        self.array('c', ('h', 'i')).tofile(f)
        f.close()
        assert open(self.tempfile, 'r').readline() == 'hi'

        a = self.array('c')
        a.fromfile(open(self.tempfile, 'r'), 2)
        assert repr(a) == "array('c', 'hi')"

        raises(ValueError, self.array('i').tounicode)
        assert self.array('u', unicode('hello')).tounicode() == \
               unicode('hello')

    def test_buffer(self):
        a = self.array('h', 'Hi')
        buf = buffer(a)
        assert buf[1] == 'i'
        #raises(TypeError, buf.__setitem__, 1, 'o')

    def test_list_methods(self):
        assert repr(self.array('i')) == "array('i')"
        assert repr(self.array('i', [1, 2, 3])) == "array('i', [1, 2, 3])"
        assert repr(self.array('h')) == "array('h')"

        a = self.array('i', [1, 2, 3, 1, 2, 1])
        assert a.count(1) == 3
        assert a.count(2) == 2
        assert a.index(3) == 2
        assert a.index(2) == 1
        raises(ValueError, a.index, 10)

        a.reverse()
        assert repr(a) == "array('i', [1, 2, 1, 3, 2, 1])"

        b = self.array('i', [1, 2, 3, 1, 2])
        b.reverse()
        assert repr(b) == "array('i', [2, 1, 3, 2, 1])"

        a.remove(3)
        assert repr(a) == "array('i', [1, 2, 1, 2, 1])"
        a.remove(1)
        assert repr(a) == "array('i', [2, 1, 2, 1])"

        a.pop()
        assert repr(a) == "array('i', [2, 1, 2])"

        a.pop(1)
        assert repr(a) == "array('i', [2, 2])"

        a.pop(-2)
        assert repr(a) == "array('i', [2])"

        a.insert(1, 7)
        assert repr(a) == "array('i', [2, 7])"
        a.insert(0, 8)
        a.insert(-1, 9)
        assert repr(a) == "array('i', [8, 2, 9, 7])"

        a.insert(100, 10)
        assert repr(a) == "array('i', [8, 2, 9, 7, 10])"
        a.insert(-100, 20)
        assert repr(a) == "array('i', [20, 8, 2, 9, 7, 10])"

    def test_compare(self):
        class comparable(object):
            def __cmp__(self, other):
                return 0
        class incomparable(object):
            pass
        
        for v1, v2, tt in (([1, 2, 3], [1, 3, 2], 'bhilBHIL'),
                         ('abc', 'acb', 'c'),
                         (unicode('abc'), unicode('acb'), 'u')):
            for t in tt:
                a = self.array(t, v1)
                b = self.array(t, v1)
                c = self.array(t, v2)

                assert (a == 7) is False
                assert (comparable() == a) is True
                assert (a == comparable()) is True
                assert (a == incomparable()) is False
                assert (incomparable() == a) is False

                assert (a == a) is True
                assert (a == b) is True
                assert (b == a) is True
                assert (a == c) is False
                assert (c == a) is False

                assert (a != a) is False
                assert (a != b) is False
                assert (b != a) is False
                assert (a != c) is True
                assert (c != a) is True

                assert (a < a) is False
                assert (a < b) is False
                assert (b < a) is False
                assert (a < c) is True
                assert (c < a) is False

                assert (a > a) is False
                assert (a > b) is False
                assert (b > a) is False
                assert (a > c) is False
                assert (c > a) is True

                assert (a <= a) is True
                assert (a <= b) is True
                assert (b <= a) is True
                assert (a <= c) is True
                assert (c <= a) is False

                assert (a >= a) is True
                assert (a >= b) is True
                assert (b >= a) is True
                assert (a >= c) is False
                assert (c >= a) is True

                assert cmp(a, a) == 0
                assert cmp(a, b) == 0
                assert cmp(a, c) <  0
                assert cmp(b, a) == 0
                assert cmp(c, a) >  0

    def test_reduce(self):
        import pickle
        a = self.array('i', [1, 2, 3])
        s = pickle.dumps(a, 1)
        b = pickle.loads(s)
        assert a == b

        a = self.array('l')
        s = pickle.dumps(a, 1)
        b = pickle.loads(s)
        assert len(b) == 0 and b.typecode == 'l'

        a = self.array('i', [1, 2, 4])
        i = iter(a)
        #raises(TypeError, pickle.dumps, i, 1)

    def test_copy_swap(self):
        a = self.array('i', [1, 2, 3])
        from copy import copy
        b = copy(a)
        a[1] = 7
        assert repr(b) == "array('i', [1, 2, 3])"

        for tc in 'bhilBHIL':
            a = self.array(tc, [1, 2, 3])
            a.byteswap()
            assert len(a) == 3
            assert a[0] == 1 * (256 ** (a.itemsize - 1))
            assert a[1] == 2 * (256 ** (a.itemsize - 1))
            assert a[2] == 3 * (256 ** (a.itemsize - 1))
            a.byteswap()
            assert len(a) == 3
            assert a[0] == 1
            assert a[1] == 2
            assert a[2] == 3

    def test_addmul(self):
        a = self.array('i', [1, 2, 3])
        assert repr(a + a) == "array('i', [1, 2, 3, 1, 2, 3])"
        assert 2 * a == a + a
        assert a * 2 == a + a
        b = self.array('i', [4, 5, 6, 7])
        assert repr(a + b) == "array('i', [1, 2, 3, 4, 5, 6, 7])"
        assert repr(2 * self.array('i')) == "array('i')"
        assert repr(self.array('i') + self.array('i')) == "array('i')"

        a = self.array('i', [1, 2])
        assert type(a + a) is self.array
        assert type(a * 2) is self.array
        assert type(2 * a) is self.array
        b = a
        a += a
        assert repr(b) == "array('i', [1, 2, 1, 2])"
        b *= 3
        assert repr(a) == "array('i', [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2])"
        assert a == b
        a += self.array('i', (7,))
        assert repr(a) == "array('i', [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 7])"

        raises(MemoryError, "a * self.maxint")
        raises(MemoryError, "a *= self.maxint")

        raises(TypeError, "a = self.array('i') + 2")
        raises(TypeError, "self.array('i') + self.array('b')")
        a = self.array('i')
        raises(TypeError, "a += 7")

        # Calling __add__ directly raises TypeError in cpython but
        # returns NotImplemented in pypy if placed within a
        # try: except TypeError: construction.
        #
        #raises(TypeError, self.array('i').__add__, (2,))
        #raises(TypeError, self.array('i').__iadd__, (2,))
        #raises(TypeError, self.array('i').__add__, self.array('b'))

        class addable(object):
            def __add__(self, other):
                return "add"

            def __radd__(self, other):
                return "radd"

        assert addable() + self.array('i') == 'add'
        assert self.array('i') + addable() == 'radd'

        a = self.array('i')
        a += addable()
        assert a == 'radd'

        a = self.array('i', [1, 2])
        assert a * -1 == self.array('i')
        b = a
        a *= -1
        assert a == self.array('i')
        assert b == self.array('i')

        a = self.array('i')
        raises(TypeError, "a * 'hi'")
        raises(TypeError, "'hi' * a")
        raises(TypeError, "a *= 'hi'")
        
        class mulable(object):
            def __mul__(self, other):
                return "mul"

            def __rmul__(self, other):
                return "rmul"
        
        assert mulable() * self.array('i') == 'mul'
        assert self.array('i') * mulable() == 'rmul'

        a = self.array('i')
        a *= mulable()
        assert a == 'rmul'

    def test_delitem(self):
        a = self.array('i', [1, 2, 3])
        del a[1]
        assert repr(a) == "array('i', [1, 3])"

        a = self.array('i', [1, 2, 3, 4, 5])
        del a[1:3]
        assert repr(a) == "array('i', [1, 4, 5])"

        a.__delslice__(0, 2)
        assert repr(a) == "array('i', [5])"

    def test_iter(self):
        a = self.array('i', [1, 2, 3])
        assert 1 in a
        b = self.array('i')
        for i in a:
            b.append(i)
        assert repr(b) == "array('i', [1, 2, 3])"

    def test_lying_iterable(self):
        class lier(object):
            def __init__(self, n):
                self.n = n

            def __len__(self):
                return 3

            def next(self):
                self.n -= 1
                if self.n < 0:
                    raise StopIteration
                return self.n

            def __iter__(self):
                return self

        assert len(lier(2)) == 3
        assert len(tuple(lier(2))) == 2
        a = self.array('i', lier(2))
        assert repr(a) == "array('i', [1, 0])"

        assert len(lier(5)) == 3
        assert len(tuple(lier(5))) == 5
        a = self.array('i', lier(5))
        assert repr(a) == "array('i', [4, 3, 2, 1, 0])"

    def test_type(self):
        for t in 'bBhHiIlLfdcu':
            assert type(self.array(t)) is self.array
            assert isinstance(self.array(t), self.array)

    def test_subclass(self):
        assert len(self.array('b')) == 0

        a = self.array('i')
        a.append(7)
        assert len(a) == 1

        array = self.array

        class adder(array):
            def __getitem__(self, i):
                return array.__getitem__(self, i) + 1

        a = adder('i', (1, 2, 3))
        assert len(a) == 3
        assert a[0] == 2

    def test_subclass_new(self):
        array = self.array
        class Image(array):
            def __new__(cls, width, height, typecode='d'):
                self = array.__new__(cls, typecode, [0] * (width * height))
                self.width = width
                self.height = height
                return self

            def _index(self, (x,y)):
                x = min(max(x, 0), self.width-1)
                y = min(max(y, 0), self.height-1)
                return y * self.width + x

            def __getitem__(self, i):
                return array.__getitem__(self, self._index(i))
            
            def __setitem__(self, i, val):
                return array.__setitem__(self, self._index(i), val)

        img = Image(5, 10, 'B')
        for y in range(10):
            for x in range(5):
                img[x, y] = x * y
        for y in range(10):
            for x in range(5):
                assert img[x, y] == x * y

        assert img[3, 25] == 3 * 9

                
    def test_override_from(self):
        class mya(self.array):
            def fromlist(self, lst):
                self.append(7)

            def fromstring(self, lst):
                self.append('8')

            def fromunicode(self, lst):
                self.append(u'9')

            def extend(self, lst):
                self.append(10)

        assert repr(mya('c', 'hi')) == "array('c', 'hi')"
        assert repr(mya('u', u'hi')) == "array('u', u'hi')"
        assert repr(mya('i', [1, 2, 3])) == "array('i', [1, 2, 3])"
        assert repr(mya('i', (1, 2, 3))) == "array('i', [1, 2, 3])"

        a = mya('i')
        a.fromlist([1, 2, 3])
        assert repr(a) == "array('i', [7])"

        a = mya('c')
        a.fromstring('hi')
        assert repr(a) == "array('c', '8')"

        a = mya('u')
        a.fromunicode(u'hi')
        assert repr(a) == "array('u', u'9')"

        a = mya('i')
        a.extend([1, 2, 3])
        assert repr(a) == "array('i', [10])"

    def test_override_to(self):
        class mya(self.array):
            def tolist(self):
                return 'list'

            def tostring(self):
                return 'str'

            def tounicode(self):
                return 'unicode'

        assert mya('i', [1, 2, 3]).tolist() == 'list'
        assert mya('c', 'hi').tostring() == 'str'
        assert mya('u', u'hi').tounicode() == 'unicode'

        assert repr(mya('c', 'hi')) == "array('c', 'hi')"
        assert repr(mya('u', u'hi')) == "array('u', u'hi')"
        assert repr(mya('i', [1, 2, 3])) == "array('i', [1, 2, 3])"
        assert repr(mya('i', (1, 2, 3))) == "array('i', [1, 2, 3])"

    def test_unicode_outofrange(self):
        a = self.array('u', unicode(r'\x01\u263a\x00\ufeff', 'unicode-escape'))
        b = self.array('u', unicode(r'\x01\u263a\x00\ufeff', 'unicode-escape'))
        b.byteswap()
        assert a != b

    def test_weakref(self):
        import weakref
        a = self.array('c', 'Hi!')
        r = weakref.ref(a)
        assert r() is a

    def test_subclass_del(self):
        import array, gc, weakref
        l = []
        
        class A(array.array):
            pass

        a = A('d')
        a.append(3.0)
        r = weakref.ref(a, lambda a: l.append(a()))
        del a
        gc.collect()
        assert l
        assert l[0] is None or len(l[0]) == 0


class TestCPythonsOwnArray(BaseArrayTests):

    def setup_class(cls):
        import array
        cls.array = array.array
        import struct
        cls.struct = struct
        cls.tempfile = str(py.test.ensuretemp('array').join('tmpfile'))
        cls.maxint = sys.maxint

class AppTestArray(BaseArrayTests):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('array', 'struct', '_rawffi'))
        cls.w_array = cls.space.appexec([], """():
            import array
            return array.array
        """)
        cls.w_tempfile = cls.space.wrap(
            str(py.test.ensuretemp('array').join('tmpfile')))
        cls.w_maxint = cls.space.wrap(sys.maxint)
    
    def test_buffer_info(self):
        a = self.array('c', 'Hi!')
        bi = a.buffer_info()
        assert bi[0] != 0
        assert bi[1] == 3
        import _rawffi
        data = _rawffi.charp2string(bi[0])
        assert data[0:3] == 'Hi!'

    def test_array_reverse_slice_assign_self(self):
        a = self.array('b', range(4))
        a[::-1] = a
        assert a == self.array('b', [3, 2, 1, 0])
