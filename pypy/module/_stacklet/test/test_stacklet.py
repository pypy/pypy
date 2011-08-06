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

    def test_propagate_exception(self):
        from _stacklet import error, newstacklet
        #
        def empty_callback(h):
            assert h.is_pending()
            seen.append(h)
            raise ValueError
        #
        seen = []
        raises(ValueError, newstacklet, empty_callback)
        assert len(seen) == 1
        assert not seen[0].is_pending()

    def test_callback_with_arguments(self):
        from _stacklet import newstacklet
        #
        def empty_callback(h, *args, **kwds):
            assert h.is_pending()
            seen.append(h)
            seen.append(args)
            seen.append(kwds)
            return h
        #
        seen = []
        h = newstacklet(empty_callback, 42, 43, foo=44, bar=45)
        assert h is None
        assert len(seen) == 3
        assert not seen[0].is_pending()
        assert seen[1] == (42, 43)
        assert seen[2] == {'foo': 44, 'bar': 45}
