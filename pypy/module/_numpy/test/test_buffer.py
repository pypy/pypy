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

    def test_buffer_set(self):
        from _numpy import array
        from _numpy import dtype
        ar = array(range(5), dtype=dtype("int8"))
        buf = ar.data

        buf[0] = '\5'
        buf[1] = '\0'

        assert ar[0] == 5
        assert ar[1] == 0

        raises(IndexError, "buf[5] = '\\9'")

    def test_slice_set(self):
        from _numpy import array
        from _numpy import dtype
        ar = array(range(5), dtype=dtype("int8"))

        view = ar[1:-1]

        arbuf = ar.data
        viewbuf = view.data

        viewbuf[0] = '\5'

        assert view[0] == 5

        arbuf[1] = '\4'
        assert view[0] == 4

        raises(IndexError, "view[4] = '\\5'")
