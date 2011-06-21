from pypy.conftest import gettestobjspace


class AppTestBuilders(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['__pypy__'])

    def test_simple(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder()
        b.append(u"abc")
        b.append(u"123")
        b.append(u"1")
        s = b.build()
        assert s == u"abc1231"
        raises(ValueError, b.build)
        raises(ValueError, b.append, u"123")

    def test_preallocate(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder(10)
        b.append(u"abc")
        b.append(u"123")
        s = b.build()
        assert s == u"abc123"