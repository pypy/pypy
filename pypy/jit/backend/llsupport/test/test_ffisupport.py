from pypy.rlib.libffi import types
from pypy.jit.backend.llsupport.ffisupport import get_call_descr_dynamic, \
    VoidCallDescr, DynamicIntCallDescr
    
def test_call_descr_dynamic():

    args = [types.sint, types.double, types.pointer]
    descr = get_call_descr_dynamic(args, types.void)
    assert isinstance(descr, VoidCallDescr)
    assert descr.arg_classes == 'ifi'

    descr = get_call_descr_dynamic([], types.sint8)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.get_result_size(False) == 1
    assert descr.is_result_signed() == True

    descr = get_call_descr_dynamic([], types.uint8)
    assert isinstance(descr, DynamicIntCallDescr)
    assert descr.get_result_size(False) == 1
    assert descr.is_result_signed() == False

    descr = get_call_descr_dynamic([], types.float)
    assert descr is None # single floats are not supported so far
    
