import autopath, py

from pypy.objspace.std.model import WITHSTRSLICE
if not WITHSTRSLICE:
    py.test.skip("WITHSTRSLICE is not enabled")


class AppTestStringObject:

    def test_basic(self):
        import sys
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('0123456789')
        assert len(s) == 10
        assert s[5] == '5'
        assert s[-2] == '8'
        assert s[3:7] == '3456'
        assert 'W_StringSliceObject' in sys.pypy_repr(s)
        assert 'W_StringSliceObject' in sys.pypy_repr(s[3:7])

    def test_find(self):
        def slice(s): return (s*3)[len(s):-len(s)]
        assert slice('abcdefghiabc').find('abc') == 0
        assert slice('abcdefghiabc').find('abc', 1) == 9
        assert slice('abcdefghiabc').find('def', 4) == -1

    def test_index(self):
        from sys import maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        assert slice('abcdefghiabc').index('') == 0
        assert slice('abcdefghiabc').index('def') == 3
        assert slice('abcdefghiabc').index('abc') == 0
        assert slice('abcdefghiabc').index('abc', 1) == 9
        assert slice('abcdefghiabc').index('def', -4*maxint, 4*maxint) == 3
        raises(ValueError, slice('abcdefghiabc').index, 'hib')
        raises(ValueError, slice('abcdefghiab').index, 'abc', 1)
        raises(ValueError, slice('abcdefghi').index, 'ghi', 8)
        raises(ValueError, slice('abcdefghi').index, 'ghi', -1)
        raises(TypeError, slice('abcdefghijklmn').index, 'abc', 0, 0.0)
        raises(TypeError, slice('abcdefghijklmn').index, 'abc', -10.0, 30)

    def test_rfind(self):
        def slice(s): return (s*3)[len(s):-len(s)]
        assert slice('abcdefghiabc').rfind('abc') == 9
        assert slice('abcdefghiabc').rfind('') == 12
        assert slice('abcdefghiabc').rfind('abcd') == 0
        assert slice('abcdefghiabc').rfind('abcz') == -1

    def test_rindex(self):
        from sys import maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        assert slice('abcdefghiabc').rindex('') == 12
        assert slice('abcdefghiabc').rindex('def') == 3
        assert slice('abcdefghiabc').rindex('abc') == 9
        assert slice('abcdefghiabc').rindex('abc', 0, -1) == 0
        assert slice('abcdefghiabc').rindex('abc', -4*maxint, 4*maxint) == 9
        raises(ValueError, slice('abcdefghiabc').rindex, 'hib')
        raises(ValueError, slice('defghiabc').rindex, 'def', 1)
        raises(ValueError, slice('defghiabc').rindex, 'abc', 0, -1)
        raises(ValueError, slice('abcdefghi').rindex, 'ghi', 0, 8)
        raises(ValueError, slice('abcdefghi').rindex, 'ghi', 0, -1)
        raises(TypeError, slice('abcdefghijklmn').rindex, 'abc', 0, 0.0)
        raises(TypeError, slice('abcdefghijklmn').rindex, 'abc', -10.0, 30)

    def test_contains(self):
        def slice(s): return (s*3)[len(s):-len(s)]
        assert '' in slice('abc')
        assert 'a' in slice('abc')
        assert 'ab' in slice('abc')
        assert not 'd' in slice('abc')
        raises(TypeError, slice('a').__contains__, 1)
        
    def test_hash(self):
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def slice(s): return (s*3)[len(s):-len(s)]
        assert hash(slice('hello')) & 0x7fffffff == 0x347697fd
        assert hash(slice('hello world!')) & 0x7fffffff == 0x2f0bb411
