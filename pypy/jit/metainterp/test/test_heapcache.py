from pypy.jit.metainterp.heapcache import HeapCache

class TestHeapCache(object):
    def test_known_class_box(self):
        h = HeapCache()
        assert not h.is_class_known(1)
        assert not h.is_class_known(2)
        h.class_now_know(1)
        assert h.is_class_known(1)
        assert not h.is_class_known(2)

        h.reset()
        assert not h.is_class_known(1)
        assert not h.is_class_known(2)

    def test_nonstandard_virtualizable(self):
        h = HeapCache()
        assert not h.is_nonstandard_virtualizable(1)
        assert not h.is_nonstandard_virtualizable(2)
        h.nonstandard_virtualizables_now_known(1)
        assert h.is_nonstandard_virtualizable(1)
        assert not h.is_nonstandard_virtualizable(2)

        h.reset()
        assert not h.is_nonstandard_virtualizable(1)
        assert not h.is_nonstandard_virtualizable(2)
