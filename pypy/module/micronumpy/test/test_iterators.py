
from pypy.module.micronumpy.interp_iter import AxisIterator
from pypy.module.micronumpy.interp_numarray import W_NDimArray

class MockDtype(object):
    def malloc(self, size):
        return None

class TestAxisIteratorDirect(object):
    def test_axis_iterator(self):
        a = W_NDimArray(7*5*3, [7, 5, 3], MockDtype(), 'C')
        i = AxisIterator(a)
        ret = []
        while not i.done:
            ret.append(i.offset)
            i.next()
        assert ret == [3*v for v in range(7*5)]
        i = AxisIterator(a,2)
        ret = []
        while not i.done:
            ret.append(i.offset)
            i.next()
        assert ret == [3*v for v in range(7*5)]
        i = AxisIterator(a,1)
        ret = []
        while not i.done:
            ret.append(i.offset)
            i.next()
        assert ret == [ 0,  1,  2, 15, 16, 17, 30, 31, 32, 45, 46, 47,
                       60, 61, 62, 75, 76, 77, 90, 91, 92] 
    def test_axis_iterator_with_start(self):
        a = W_NDimArray(7*5*3, [7, 5, 3], MockDtype(), 'C')
        i = AxisIterator(a, start=[0, 0, 0])
        ret = []
        while not i.done:
            ret.append(i.offset)
            i.next()
        assert ret == [3*v for v in range(7*5)]
        i = AxisIterator(a, start=[1, 1, 0])
        ret = []
        while not i.done:
            ret.append(i.offset)
            i.next()
        assert ret == [3*v+18 for v in range(7*5)]
        i = AxisIterator(a, 1, [2, 0, 2])
        ret = []
        while not i.done:
            ret.append(i.offset)
            i.next()
        assert ret == [v + 32 for v in [ 0,  1,  2, 15, 16, 17, 30, 31, 32,
                            45, 46, 47, 60, 61, 62, 75, 76, 77, 90, 91, 92]]
