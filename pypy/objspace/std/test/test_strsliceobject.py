import py

from pypy.objspace.std.test import test_stringobject
from pypy.conftest import gettestobjspace
from pypy.interpreter import gateway
from pypy.objspace.std.strsliceobject import W_StringSliceObject

class AppTestStringObject(test_stringobject.AppTestStringObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withstrslice": True})
        def not_forced(space, w_s):
            return space.wrap(isinstance(w_s, W_StringSliceObject) and
                              (w_s.start != 0 or w_s.stop != len(w_s.str)))
        cls.w_not_forced = cls.space.wrap(gateway.interp2app(not_forced))

    def test_basic(self):
        import __pypy__
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('0123456789' * 20)
        assert len(s) == 200
        assert self.not_forced(s)
        assert s[5] == '5'
        assert s[-2] == '8'
        assert s[3:7] == '3456'
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        # when the slice is too short, don't use the slice string object
        assert 'W_StringObject' in __pypy__.internal_repr("abcdefgh"[3:7])
        s2 = s.upper()
        assert not self.not_forced(s)

    def test_find(self):
        import __pypy__
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('abcdefghiabc' + "X" * 100)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert slice('abcdefghiabc' + 'X' * 100) == 'abcdefghiabc' + 'X' * 100
        res = s.find('abc')
        assert res == 0
        assert s.find('abc', 1) == 9
        assert s.find('def', 4) == -1

    def test_index(self):
        import __pypy__, sys
        m = sys.maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('abcdefghiabc' * 20)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
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
        import __pypy__
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('abcdefghiabc' + "X" * 100)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert s.rfind('abc') == 9
        assert s.rfind('') == 112
        assert s.rfind('abcd') == 0
        assert s.rfind('abcz') == -1

    def test_rindex(self):
        import __pypy__
        from sys import maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice("X" * 100 + 'abcdefghiabc')
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
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
        import __pypy__
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice("abc" + "X" * 100)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert '' in s
        assert 'a' in s
        assert 'ab' in s
        assert not 'd' in s
        raises(TypeError, slice('a' * 100).__contains__, 1)
        
    def test_hash(self):
        import __pypy__
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice('a' * 101)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert hash(s) & 0x7fffffff == 0x7e0bce58

    def test_split_produces_strslices(self):
        import __pypy__
        l = ("X" * 100 + "," + "Y" * 100).split(",")
        assert "W_StringSliceObject" in __pypy__.internal_repr(l[0])
        assert "W_StringSliceObject" in __pypy__.internal_repr(l[1])

    def test_strip_produces_strslices(self):
        import __pypy__
        s = ("abc" + "X" * 100 + "," + "Y" * 100 + "abc").strip("abc")
        assert "W_StringSliceObject" in __pypy__.internal_repr(s)

    def test_splitlines_produces_strslices(self):
        import __pypy__
        l = ("X" * 100 + "\n" + "Y" * 100).splitlines()
        assert "W_StringSliceObject" in __pypy__.internal_repr(l[0])
        assert "W_StringSliceObject" in __pypy__.internal_repr(l[1])

    def test_count_does_not_force(self):
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice("X" * 100 + "\n" + "Y" * 100)
        assert s.count("X") == 100
        assert s.count("Y") == 100
        assert self.not_forced(s)
