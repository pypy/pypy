import py
from pypy.module.micronumpy.interp_iter import ViewIterator

class TestIterDirect(object):
    def test_viewiterator(self):
        i = ViewIterator(0, [5, 1], [10, 4], [3, 5])
        i = i.next(2)
        i = i.next(2)
        i = i.next(2)
        assert i.offset == 3
        assert not i.done()
        assert i.indices == [0,3]
