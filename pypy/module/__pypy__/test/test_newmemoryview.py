

class AppTestMinimal:
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_newmemoryview(self):
        from __pypy__ import newmemoryview
        b = bytearray(12)
        # The format can be anything, we only verify shape, strides, and itemsize
        m = newmemoryview(memoryview(b), 2, 'T{<h:a}', shape=(2, 3))
        assert m.strides == (6, 2)
        m = newmemoryview(memoryview(b), 2, 'T{<h:a}', shape=(2, 3),
                          strides=(6, 2))
        assert m.strides == (6, 2)
        assert m.format == 'T{<h:a}'
        assert m.itemsize == 2
