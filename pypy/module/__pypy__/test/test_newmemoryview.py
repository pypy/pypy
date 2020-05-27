

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

    def test_empty(self):
        from __pypy__ import newmemoryview
        b = bytearray(0)
        m = newmemoryview(memoryview(b), 0, 'B', (42,))
        assert m.tobytes() == b''
        assert m.shape == (42,)
        assert m.strides == (0,)
        with raises(ValueError):
            newmemoryview(memoryview(b), 0, 'B')

    def test_bufferable(self):
        from __pypy__ import bufferable, newmemoryview
        class B(bufferable.bufferable):
            def __init__(self):
                self.data = bytearray(b'abc')

            def __buffer__(self, flags):
                return newmemoryview(memoryview(self.data), 1, 'B')


        obj = B()
        buf = buffer(obj)
        v = obj.data[2]
        assert ord(buf[2]) == v
