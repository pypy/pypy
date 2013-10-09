# side-effect: FORMAT_LONGDOUBLE must be built before test_checkmodule()
from pypy.module._cffi_backend import misc
from pypy.module._cffi_backend.ctypeptr import W_CTypePtrOrArray

class AppTestFastPath(object):
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

