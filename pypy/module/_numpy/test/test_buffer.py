from pypy.module._numpy.test.test_base import BaseNumpyAppTest

class AppTestNumArray(BaseNumpyAppTest):
    def test_access(self):
        from _numpy import array
        from _numpy import dtype
        ar = array(range(5), dtype=dtype("int8"))
        buf = ar.data

        assert buf[0] == '\0'
        assert buf[1] == '\1'

        raises(IndexError, "buf[5]")

    def test_mutable(self):
        from _numpy import array
        from _numpy import dtype
        ar = array(range(5), dtype=dtype("int8"))
        buf = ar.data
        assert buf[0] == '\0'

        ar[0] = 5
        assert buf[0] == "\5"

    def test_slice_view(self):
        skip("buffers on slicing views doesn't work yet")
        from _numpy import array
        from _numpy import dtype
        ar = array(range(5), dtype=dtype("int8"))

        view = ar[1:-1]

        arbuf = ar.data
        viewbuf = view.data

        ar[1] = 5

        assert ar[1] == view[0] == 5

        assert arbuf[1] == '\5'
        assert viewbuf[0] == '\5'
