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
