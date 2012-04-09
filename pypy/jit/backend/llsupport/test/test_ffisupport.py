from pypy.rlib.libffi import types
from pypy.jit.codewriter.longlong import is_64_bit
from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport.ffisupport import *
from pypy.rlib.rarithmetic import is_emulated_long


class FakeCPU:
    def __init__(self, supports_floats=False, supports_longlong=False,
                 supports_singlefloats=False):
        self.supports_floats = supports_floats
        self.supports_longlong = supports_longlong
        self.supports_singlefloats = supports_singlefloats


def test_call_descr_dynamic():
    args = [types.sint, types.pointer]
    descr = get_call_descr_dynamic(FakeCPU(), args, types.sint, None,
                                   ffi_flags=42)
    assert isinstance(descr, CallDescr)
    assert descr.result_type == 'i'
    assert descr.result_flag == FLAG_SIGNED
    assert descr.arg_classes == 'ii'
    assert descr.get_ffi_flags() == 42

    args = [types.sint, types.double, types.pointer]
    descr = get_call_descr_dynamic(FakeCPU(), args, types.void, None, 42)
    assert descr is None    # missing floats
    descr = get_call_descr_dynamic(FakeCPU(supports_floats=True),
                                   args, types.void, None, ffi_flags=43)
    assert descr.result_type == 'v'
    assert descr.result_flag == FLAG_VOID
    assert descr.arg_classes == 'ifi'
    assert descr.get_ffi_flags() == 43

    descr = get_call_descr_dynamic(FakeCPU(), [], types.sint8, None, 42)
    assert descr.get_result_size() == 1
    assert descr.result_flag == FLAG_SIGNED
    assert descr.is_result_signed() == True

    descr = get_call_descr_dynamic(FakeCPU(), [], types.uint8, None, 42)
    assert isinstance(descr, CallDescr)
    assert descr.get_result_size() == 1
    assert descr.result_flag == FLAG_UNSIGNED
    assert descr.is_result_signed() == False

    if not is_64_bit or is_emulated_long:
        descr = get_call_descr_dynamic(FakeCPU(), [], types.slonglong,
                                       None, 42)
        assert descr is None   # missing longlongs
        descr = get_call_descr_dynamic(FakeCPU(supports_longlong=True),
                                       [], types.slonglong, None, ffi_flags=43)
        assert isinstance(descr, CallDescr)
        assert descr.result_flag == FLAG_FLOAT
        assert descr.result_type == 'L'
        assert descr.get_ffi_flags() == 43
    else:
        assert types.slonglong is types.slong

    descr = get_call_descr_dynamic(FakeCPU(), [], types.float, None, 42)
    assert descr is None   # missing singlefloats
    descr = get_call_descr_dynamic(FakeCPU(supports_singlefloats=True),
                                   [], types.float, None, ffi_flags=44)
    assert descr.result_flag == FLAG_UNSIGNED
    assert descr.result_type == 'S'
    assert descr.get_ffi_flags() == 44
