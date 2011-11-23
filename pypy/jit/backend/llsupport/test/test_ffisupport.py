from pypy.rlib.libffi import types
from pypy.jit.codewriter.longlong import is_64_bit
from pypy.jit.backend.llsupport.ffisupport import *


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
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.arg_classes == 'ii'
    assert descr.get_ffi_flags() == 42

    args = [types.sint, types.double, types.pointer]
    descr = get_call_descr_dynamic(FakeCPU(), args, types.void, None, 42)
    assert descr is None    # missing floats
    descr = get_call_descr_dynamic(FakeCPU(supports_floats=True),
                                   args, types.void, None, ffi_flags=43)
    assert isinstance(descr, VoidCallDescr)
    assert descr.arg_classes == 'ifi'
    assert descr.get_ffi_flags() == 43

    descr = get_call_descr_dynamic(FakeCPU(), [], types.sint8, None, 42)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.get_result_size(False) == 1
    assert descr.is_result_signed() == True

    descr = get_call_descr_dynamic(FakeCPU(), [], types.uint8, None, 42)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.get_result_size(False) == 1
    assert descr.is_result_signed() == False

    if not is_64_bit:
        descr = get_call_descr_dynamic(FakeCPU(), [], types.slonglong,
                                       None, 42)
        assert descr is None   # missing longlongs
        descr = get_call_descr_dynamic(FakeCPU(supports_longlong=True),
                                       [], types.slonglong, None, ffi_flags=43)
        assert isinstance(descr, LongLongCallDescr)
        assert descr.get_ffi_flags() == 43
    else:
        assert types.slonglong is types.slong

    descr = get_call_descr_dynamic(FakeCPU(), [], types.float, None, 42)
    assert descr is None   # missing singlefloats
    descr = get_call_descr_dynamic(FakeCPU(supports_singlefloats=True),
                                   [], types.float, None, ffi_flags=44)
    SingleFloatCallDescr = getCallDescrClass(rffi.FLOAT)
    assert isinstance(descr, SingleFloatCallDescr)
    assert descr.get_ffi_flags() == 44
