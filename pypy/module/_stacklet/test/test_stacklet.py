import os
from pypy.conftest import gettestobjspace


class AppTestStacklet:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_stacklet'])
        cls.w_translated = cls.space.wrap(
            os.path.join(os.path.dirname(__file__),
                         'test_translated.py'))

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

    def test_type_of_h(self):
        from _stacklet import newstacklet, Stacklet
        #
        def empty_callback(h):
            seen.append(type(h))
            return h
        #
        seen = []
        h = newstacklet(empty_callback)
        assert h is None
        assert seen[0] is Stacklet

    def test_switch(self):
        from _stacklet import newstacklet
        #
        def switchbackonce_callback(h):
            seen.append(1)
            assert h.is_pending()
            h2 = h.switch()
            seen.append(3)
            assert not h.is_pending()
            assert h2.is_pending()
            return h2
        #
        seen = []
        h = newstacklet(switchbackonce_callback)
        seen.append(2)
        assert h.is_pending()
        h2 = h.switch()
        assert h2 is None
        assert seen == [1, 2, 3]

    def test_go_depth2(self):
        from _stacklet import newstacklet
        #
        def depth2(h):
            seen.append(2)
            return h
        #
        def depth1(h):
            seen.append(1)
            h2 = newstacklet(depth2)
            assert h2 is None
            seen.append(3)
            return h
        #
        seen = []
        h = newstacklet(depth1)
        assert h is None
        assert seen == [1, 2, 3]

    def test_exception_depth2(self):
        from _stacklet import newstacklet
        #
        def depth2(h):
            seen.append(2)
            raise ValueError
        #
        def depth1(h):
            seen.append(1)
            try:
                newstacklet(depth2)
            except ValueError:
                seen.append(3)
            return h
        #
        seen = []
        h = newstacklet(depth1)
        assert h is None
        assert seen == [1, 2, 3]

    def test_exception_with_switch(self):
        from _stacklet import newstacklet
        #
        def depth1(h):
            seen.append(1)
            h = h.switch()
            seen.append(3)
            raise ValueError
        #
        seen = []
        h = newstacklet(depth1)
        seen.append(2)
        raises(ValueError, h.switch)
        assert seen == [1, 2, 3]

    def test_exception_with_switch_depth2(self):
        from _stacklet import newstacklet
        #
        def depth2(h):
            seen.append(4)
            h = h.switch()
            seen.append(6)
            raise ValueError
        #
        def depth1(h):
            seen.append(1)
            h = h.switch()
            seen.append(3)
            h2 = newstacklet(depth2)
            seen.append(5)
            raises(ValueError, h2.switch)
            assert not h2.is_pending()
            seen.append(7)
            raise KeyError
        #
        seen = []
        h = newstacklet(depth1)
        seen.append(2)
        raises(KeyError, h.switch)
        assert not h.is_pending()
        assert seen == [1, 2, 3, 4, 5, 6, 7]

    def test_various_depths(self):
        skip("may fail on top of CPython")
        # run it from test_translated, but not while being actually translated
        d = {}
        execfile(self.translated, d)
        d['set_fast_mode']()
        d['test_various_depths']()
