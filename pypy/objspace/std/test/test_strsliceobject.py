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
        s = slice(b'0123456789' * 20)
        assert len(s) == 200
        assert self.not_forced(s)
        assert s[5] == b'5'
        assert s[-2] == b'8'
        assert s[3:7] == b'3456'
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        # when the slice is too short, don't use the slice string object
        assert 'W_StringObject' in __pypy__.internal_repr(b"abcdefgh"[3:7])
        s2 = s.upper()
        assert not self.not_forced(s)

    def test_find(self):
        import __pypy__
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice(b'abcdefghiabc' + b"X" * 100)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert slice(b'abcdefghiabc' + b'X' * 100) == b'abcdefghiabc' + b'X' * 100
        res = s.find(b'abc')
        assert res == 0
        assert s.find(b'abc', 1) == 9
        assert s.find(b'def', 4) == -1

    def test_index(self):
        import __pypy__, sys
        m = sys.maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice(b'abcdefghiabc' * 20)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert s.index(b'') == 0
        assert s.index(b'def') == 3
        assert s.index(b'abc') == 0
        assert s.index(b'abc', 1) == 9
        assert s.index(b'def', -4*m, 4*m) == 3
        raises(ValueError, s.index, b'hib')
        raises(ValueError, slice(b'abcdefghiab' + b"X" * 100).index, b'abc', 1)
        raises(ValueError, slice(b'abcdefghi'  + b"X" * 20).index, b'ghi', 8)
        raises(ValueError, slice(b'abcdefghi' + b"X" * 20).index, b'ghi', -1)
        raises(TypeError, slice(b'abcdefghijklmn' * 20).index, b'abc', 0, 0.0)
        raises(TypeError, slice(b'abcdefghijklmn' * 20).index, b'abc', -10.0, 30)

    def test_rfind(self):
        import __pypy__
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice(b'abcdefghiabc' + b"X" * 100)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert s.rfind(b'abc') == 9
        assert s.rfind(b'') == 112
        assert s.rfind(b'abcd') == 0
        assert s.rfind(b'abcz') == -1

    def test_rindex(self):
        import __pypy__
        from sys import maxint
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice(b"X" * 100 + b'abcdefghiabc')
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert s.rindex(b'') == 112
        assert s.rindex(b'def') == 103
        assert s.rindex(b'abc') == 109
        assert s.rindex(b'abc', 0, -1) == 100
        assert s.rindex(b'abc', -4*maxint, 4*maxint) == 109
        raises(ValueError, slice(b'abcdefghiabc' * 20).rindex, b'hib')
        raises(ValueError, slice(b'defghiabc' + b"X" * 100).rindex, b'def', 1)
        raises(ValueError, slice(b'defghiabc' + b"X" * 100).rindex, b'abc', 0, -101)
        raises(ValueError, slice(b'abcdefghi' + b"X" * 100).rindex, b'ghi', 0, 8)
        raises(ValueError, slice(b'abcdefghi' + b"X" * 100).rindex, b'ghi', 0, -101)
        raises(TypeError, slice(b'abcdefghijklmn' + b"X" * 100).rindex,
               b'abc', 0, 0.0)
        raises(TypeError, slice(b'abcdefghijklmn' + b"X" * 100).rindex,
               b'abc', -10.0, 30)

    def test_contains(self):
        import __pypy__
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice(b"abc" + b"X" * 100)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert b'' in s
        assert b'a' in s
        assert b'ab' in s
        assert not b'd' in s
        assert ord(b'a') in slice(b'a' * 100)
        
    def test_hash(self):
        import __pypy__
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice(b'a' * 101)
        assert 'W_StringSliceObject' in __pypy__.internal_repr(s)
        assert hash(s) & 0x7fffffff == 0x7e0bce58

    def test_strip_produces_strslices(self):
        import __pypy__
        s = (b"abc" + b"X" * 100 + b"," + b"Y" * 100 + b"abc").strip(b"abc")
        assert "W_StringSliceObject" in __pypy__.internal_repr(s)

    def test_splitlines_produces_strslices(self):
        import __pypy__
        l = (b"X" * 100 + b"\n" + b"Y" * 100).splitlines()
        assert "W_StringSliceObject" in __pypy__.internal_repr(l[0])
        assert "W_StringSliceObject" in __pypy__.internal_repr(l[1])

    def test_count_does_not_force(self):
        def slice(s): return (s*3)[len(s):-len(s)]
        s = slice(b"X" * 100 + b"\n" + b"Y" * 100)
        assert s.count(b"X") == 100
        assert s.count(b"Y") == 100
        assert self.not_forced(s)

    def test_extended_slice(self):
        import __pypy__
        def slice1(s): return (s*3)[len(s):-len(s)]
        s = slice1(b'0123456789' * 20)
        assert len(s) == 200
        assert self.not_forced(s)
        t = s[::-1]
        assert t == b'9876543210' * 20
        assert not self.not_forced(t)
        u = s[slice(10, 20)]
        assert self.not_forced(u)
        assert u == b'0123456789'
