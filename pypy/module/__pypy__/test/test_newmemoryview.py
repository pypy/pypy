

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

    def test_bufferable(self):
        from __pypy__ import bufferable, newmemoryview
        class B(bufferable.bufferable):
            def __init__(self):
                self.data = bytearray(b'abc')

            def __buffer__(self, flags):
                return newmemoryview(memoryview(self.data), 1, 'B')


        obj = B()
        buf = memoryview(obj)
        v = obj.data[2]
        assert buf[2] == v

