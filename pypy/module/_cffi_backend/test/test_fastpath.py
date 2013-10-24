# side-effect: FORMAT_LONGDOUBLE must be built before test_checkmodule()
from pypy.module._cffi_backend import misc
from pypy.module._cffi_backend.ctypeptr import W_CTypePtrOrArray

class AppTest_fast_path_from_list(object):
    spaceconfig = dict(usemodules=('_cffi_backend', 'cStringIO'))

    def setup_method(self, meth):
        def forbidden(self, *args):
            assert False, 'The slow path is forbidden'
        self._original = W_CTypePtrOrArray._convert_array_from_listview.im_func
        W_CTypePtrOrArray._convert_array_from_listview = forbidden

    def teardown_method(self, meth):
        W_CTypePtrOrArray._convert_array_from_listview = self._original

    def test_fast_init_from_list(self):
        import _cffi_backend
        LONG = _cffi_backend.new_primitive_type('long')
        P_LONG = _cffi_backend.new_pointer_type(LONG)
        LONG_ARRAY = _cffi_backend.new_array_type(P_LONG, None)
        buf = _cffi_backend.newp(LONG_ARRAY, [1, 2, 3])
        assert buf[0] == 1
        assert buf[1] == 2
        assert buf[2] == 3

    def test_fast_init_from_list_float(self):
        import _cffi_backend
        DOUBLE = _cffi_backend.new_primitive_type('double')
        P_DOUBLE = _cffi_backend.new_pointer_type(DOUBLE)
        DOUBLE_ARRAY = _cffi_backend.new_array_type(P_DOUBLE, None)
        buf = _cffi_backend.newp(DOUBLE_ARRAY, [1.1, 2.2, 3.3])
        assert buf[0] == 1.1
        assert buf[1] == 2.2
        assert buf[2] == 3.3


class AppTest_fast_path_to_list(object):
    spaceconfig = dict(usemodules=('_cffi_backend', 'cStringIO'))

    def setup_method(self, meth):
        from pypy.interpreter import gateway
        from rpython.rlib import rarray
        #
        self.count = 0
        def get_count(*args):
            return self.space.wrap(self.count)
        self.w_get_count = self.space.wrap(gateway.interp2app(get_count))
        #
        original = rarray.populate_list_from_raw_array
        def populate_list_from_raw_array(*args):
            self.count += 1
            return original(*args)
        self._original = original
        rarray.populate_list_from_raw_array = populate_list_from_raw_array
        #
        self.w_runappdirect = self.space.wrap(self.runappdirect)


    def teardown_method(self, meth):
        from rpython.rlib import rarray
        rarray.populate_list_from_raw_array = self._original

    def test_list_int(self):
        import _cffi_backend
        LONG = _cffi_backend.new_primitive_type('long')
        P_LONG = _cffi_backend.new_pointer_type(LONG)
        LONG_ARRAY = _cffi_backend.new_array_type(P_LONG, 3)
        buf = _cffi_backend.newp(LONG_ARRAY)
        buf[0] = 1
        buf[1] = 2
        buf[2] = 3
        lst = list(buf)
        assert lst == [1, 2, 3]
        if not self.runappdirect:
            assert self.get_count() == 1

    def test_TypeError_if_no_length(self):
        import _cffi_backend
        LONG = _cffi_backend.new_primitive_type('long')
        P_LONG = _cffi_backend.new_pointer_type(LONG)
        LONG_ARRAY = _cffi_backend.new_array_type(P_LONG, 3)
        buf = _cffi_backend.newp(LONG_ARRAY)
        pbuf = _cffi_backend.cast(P_LONG, buf)
        raises(TypeError, "list(pbuf)")

    def test_bug(self):
        import _cffi_backend
        LONG = _cffi_backend.new_primitive_type('long')
        five = _cffi_backend.cast(LONG, 5)
        raises(TypeError, list, five)
        DOUBLE = _cffi_backend.new_primitive_type('double')
        five_and_a_half = _cffi_backend.cast(DOUBLE, 5.5)
        raises(TypeError, list, five_and_a_half)

    def test_list_float(self):
        import _cffi_backend
        DOUBLE = _cffi_backend.new_primitive_type('double')
        P_DOUBLE = _cffi_backend.new_pointer_type(DOUBLE)
        DOUBLE_ARRAY = _cffi_backend.new_array_type(P_DOUBLE, 3)
        buf = _cffi_backend.newp(DOUBLE_ARRAY)
        buf[0] = 1.1
        buf[1] = 2.2
        buf[2] = 3.3
        lst = list(buf)
        assert lst == [1.1, 2.2, 3.3]
        if not self.runappdirect:
            assert self.get_count() == 1
