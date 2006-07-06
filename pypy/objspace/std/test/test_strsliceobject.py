import autopath, py

from pypy.objspace.std.model import WITHSTRSLICE
if not WITHSTRSLICE:
    py.test.skip("WITHSTRSLICE is not enabled")


class AppTestStringObject:

    def test_basic(self):
        import sys
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('0123456789' * 20)
        assert len(s) == 200
        assert s[5] == '5'
        assert s[-2] == '8'
        assert s[3:7] == '3456'
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        # when the slice is too short, don't use the slice string object
        assert 'W_StringObject' in sys.pypy_repr(s[3:7])

    def test_find(self):
        import sys
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('abcdefghiabc' + "X" * 100)
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        assert s.find('abc') == 0
        assert s.find('abc', 1) == 9
        assert s.find('def', 4) == -1

    def test_index(self):
        import sys
        m = sys.maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('abcdefghiabc' * 20)
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        assert s.index('') == 0
        assert s.index('def') == 3
        assert s.index('abc') == 0
        assert s.index('abc', 1) == 9
        assert s.index('def', -4*m, 4*m) == 3
        raises(ValueError, s.index, 'hib')
        raises(ValueError, slice('abcdefghiab' + "X" * 100).index, 'abc', 1)
        raises(ValueError, slice('abcdefghi'  + "X" * 20).index, 'ghi', 8)
        raises(ValueError, slice('abcdefghi' + "X" * 20).index, 'ghi', -1)
        raises(TypeError, slice('abcdefghijklmn' * 20).index, 'abc', 0, 0.0)
        raises(TypeError, slice('abcdefghijklmn' * 20).index, 'abc', -10.0, 30)

    def test_rfind(self):
        import sys
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('abcdefghiabc' + "X" * 100)
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        assert s.rfind('abc') == 9
        assert s.rfind('') == 112
        assert s.rfind('abcd') == 0
        assert s.rfind('abcz') == -1

    def test_rindex(self):
        import sys
        from sys import maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice("X" * 100 + 'abcdefghiabc')
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        assert s.rindex('') == 112
        assert s.rindex('def') == 103
        assert s.rindex('abc') == 109
        assert s.rindex('abc', 0, -1) == 100
        assert s.rindex('abc', -4*maxint, 4*maxint) == 109
        raises(ValueError, slice('abcdefghiabc' * 20).rindex, 'hib')
        raises(ValueError, slice('defghiabc' + "X" * 100).rindex, 'def', 1)
        raises(ValueError, slice('defghiabc' + "X" * 100).rindex, 'abc', 0, -101)
        raises(ValueError, slice('abcdefghi' + "X" * 100).rindex, 'ghi', 0, 8)
        raises(ValueError, slice('abcdefghi' + "X" * 100).rindex, 'ghi', 0, -101)
        raises(TypeError, slice('abcdefghijklmn' + "X" * 100).rindex,
               'abc', 0, 0.0)
        raises(TypeError, slice('abcdefghijklmn' + "X" * 100).rindex,
               'abc', -10.0, 30)

    def test_contains(self):
        import sys
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice("abc" + "X" * 100)
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        assert '' in s
        assert 'a' in s
        assert 'ab' in s
        assert not 'd' in s
        raises(TypeError, slice('a' * 100).__contains__, 1)
        
    def test_hash(self):
        import sys
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('a' * 101)
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        assert hash(s) & 0x7fffffff == 0x7e0bce58
