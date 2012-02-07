from pypy.conftest import gettestobjspace


class AppTestBuilders(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['__pypy__'])

    def test_simple(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder()
        b.append("abc")
        b.append("123")
        b.append("1")
        s = b.build()
        assert s == "abc1231"
        raises(ValueError, b.build)
        raises(ValueError, b.append, "123")

    def test_preallocate(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder(10)
        b.append("abc")
        b.append("123")
        s = b.build()
        assert s == "abc123"

    def test_append_slice(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder()
        b.append_slice("abcdefgh", 2, 5)
        raises(ValueError, b.append_slice, "1", 2, 1)
        s = b.build()
        assert s == "cde"
        raises(ValueError, b.append_slice, "abc", 1, 2)

    def test_stringbuilder(self):
        from __pypy__.builders import StringBuilder
        b = StringBuilder()
        b.append(b"abc")
        b.append(b"123")
        assert len(b) == 6
        b.append(b"you and me")
        s = b.build()
        raises(ValueError, len, b)
        assert s == b"abc123you and me"
        raises(ValueError, b.build)
