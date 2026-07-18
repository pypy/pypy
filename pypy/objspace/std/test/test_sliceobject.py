import sys
from pypy.objspace.std.sliceobject import normalize_simple_slice


class TestW_SliceObject:

    def test_unpack(self):
        space = self.space
        w = space.wrap
        w_None = space.w_None
        w_slice = space.newslice(w_None, w_None, w_None)
        assert w_slice.unpack(space) == (0, sys.maxint, 1)
        w_slice = space.newslice(w(0), w(6), w(1))
        assert w_slice.unpack(space) == (0, 6, 1)
        w_slice = space.newslice(w_None, w_None, w(-1))
        assert w_slice.unpack(space) == (sys.maxint, -sys.maxint-1, -1)

    def test_indices(self):
        space = self.space
        w = space.wrap
        w_None = space.w_None
        w_slice = space.newslice(w_None, w_None, w_None)
        assert w_slice.indices3(space, 6) == (0, 6, 1)
        w_slice = space.newslice(w(0), w(6), w(1))
        assert w_slice.indices3(space, 6) == (0, 6, 1)
        w_slice = space.newslice(w_None, w_None, w(-1))
        assert w_slice.indices3(space, 6) == (5, -1, -1)

    def test_indices_fail(self):
        space = self.space
        w = space.wrap
        w_None = space.w_None
        w_slice = space.newslice(w_None, w_None, w(0))
        self.space.raises_w(space.w_ValueError, w_slice.indices3, space, 10)

    def test_normalize_simple_slice(self):
        space = self.space
        w = space.wrap

        def getslice(length, start, stop):
            # returns range(length)[start:stop] but without special
            # support for negative start or stop
            return [i for i in range(length) if start <= i < stop]

        assert getslice(10, 2, 5) == [2, 3, 4]

        for length in range(5):
            for start in range(-2*length-2, 2*length+3):
                for stop in range(-2*length-2, 2*length+3):
                    mystart, mystop = normalize_simple_slice(space, length,
                                                             w(start), w(stop))
                    assert 0 <= mystart <= mystop <= length
                    assert (getslice(length, start, stop) ==
                            getslice(length, mystart, mystop))


    def test_indexes4(self):
        space = self.space
        w = space.wrap

        def getslice(length, start, stop, step):
            return [i for i in range(0, length, step) if start <= i < stop]

        for step in [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, None]:
            for length in range(5):
                for start in range(-2*length-2, 2*length+3) + [None]:
                    for stop in range(-2*length-2, 2*length+3) + [None]:
                        sl = space.newslice(w(start), w(stop), w(step))
                        mystart, mystop, mystep, slicelength = sl.indices4(space, length)
                        assert len(range(length)[start:stop:step]) == slicelength
                        assert slice(start, stop, step).indices(length) == (
                                mystart, mystop, mystep)
