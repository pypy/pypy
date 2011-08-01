from pypy.rlib.libffi import types
from pypy.jit.backend.llsupport.ffisupport import *


class FakeCPU:
    def __init__(self, supports_floats=False, supports_longlong=False,
                 supports_singlefloats=False):
        self.supports_floats = supports_floats
        self.supports_longlong = supports_longlong
        self.supports_singlefloats = supports_singlefloats


def test_call_descr_dynamic():
    args = [types.sint, types.pointer]
    descr = get_call_descr_dynamic(FakeCPU(), args, types.sint)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.arg_classes == 'ii'

    args = [types.sint, types.double, types.pointer]
    descr = get_call_descr_dynamic(FakeCPU(), args, types.void)
    assert descr is None    # missing floats
    descr = get_call_descr_dynamic(FakeCPU(supports_floats=True),
                                   args, types.void)
    assert isinstance(descr, VoidCallDescr)
    assert descr.arg_classes == 'ifi'

    descr = get_call_descr_dynamic(FakeCPU(), [], types.sint8)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.get_result_size(False) == 1
    assert descr.is_result_signed() == True

    descr = get_call_descr_dynamic(FakeCPU(), [], types.uint8)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.get_result_size(False) == 1
    assert descr.is_result_signed() == False

    descr = get_call_descr_dynamic(FakeCPU(), [], types.slonglong)
    assert descr is None   # missing longlongs
    descr = get_call_descr_dynamic(FakeCPU(supports_longlong=True),
                                   [], types.slonglong)
    assert isinstance(descr, LongLongCallDescr)

    descr = get_call_descr_dynamic(FakeCPU(), [], types.float)
    assert descr is None   # missing singlefloats
    descr = get_call_descr_dynamic(FakeCPU(supports_singlefloats=True),
                                   [], types.float)
    SingleFloatCallDescr = getCallDescrClass(rffi.FLOAT)
    assert isinstance(descr, SingleFloatCallDescr)
