from pypy.conftest import gettestobjspace


class AppTestStacklet:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_stacklet'])

    def test_new_empty(self):
        from _stacklet import newstacklet
        #
        def empty_callback(h):
            assert h.is_pending()
            seen.append(1)
            return h
        #
        seen = []
        h = newstacklet(empty_callback)
        assert h is None
        assert seen == [1]

    def test_bogus_return_value(self):
        from _stacklet import error, newstacklet
        #
        def empty_callback(h):
            assert h.is_pending()
            seen.append(h)
            return 42
        #
        seen = []
        raises(TypeError, newstacklet, empty_callback)
        assert len(seen) == 1
        assert not seen[0].is_pending()
