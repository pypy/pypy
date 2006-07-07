import autopath, py

from pypy.objspace.std.model import WITHSTRJOIN
if not WITHSTRJOIN:
    py.test.skip("WITHSTRJOIN is not enabled")

class AppTestStringObject:
    def test_basic(self):
        import sys
        s = "Hello, " + "World!"
        assert type(s) is str
        assert 'W_StringJoinObject' in sys.pypy_repr(s)

    def test_add(self):
        import sys
        all = ""
        for i in range(20):
            all += str(i)
        assert 'W_StringJoinObject' in sys.pypy_repr(all)

    def test_hash(self):
        import sys
        # check that we have the same hash as CPython for at least 31 bits
        # (but don't go checking CPython's special case -1)
        # disabled: assert hash('') == 0 --- different special case
        def join(s): return s[:len(s) // 2] + s[len(s) // 2:]
        s = join('a' * 101)
        assert 'W_StringJoinObject' in sys.pypy_repr(s)
        assert hash(s) & 0x7fffffff == 0x7e0bce58

    def test_len(self):
        import sys
        s = "a" + "b"
        r = "c" + "d"
        t = s + r
        assert len(s) == 2
