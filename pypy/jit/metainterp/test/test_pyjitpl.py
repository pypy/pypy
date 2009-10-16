
# some unit tests for the bytecode decoding

from pypy.jit.metainterp import pyjitpl, codewriter, resoperation
from pypy.jit.metainterp.history import AbstractFailDescr

def make_frame(code):
    bytecode = codewriter.JitCode("hello")
    bytecode.code = code
    bytecode.constants = None
    frame = pyjitpl.MIFrame(None, bytecode)
    frame.pc = 0
    return frame


def test_decode_big_int():
    for code, value in [("\x80\x01", 128), ("\x81\x81\x01", 1 + (1 << 7) + (1 << 14))]:
        frame = make_frame(code)
        val = frame.load_int()
        assert val == value
 
def test_decode_bool():
    frame = make_frame("\x00")
    assert not frame.load_bool()

    frame = make_frame("\x01")
    assert frame.load_bool()

def test_simple_opimpl_exist():
    rop = resoperation.rop
    for opnum, opname in resoperation.opname.items():
        if opnum in (rop.SAME_AS, rop.CALL_PURE, rop.OOSEND_PURE):
            continue
        if rop._NOSIDEEFFECT_FIRST <= opnum <= rop._NOSIDEEFFECT_LAST:
            assert hasattr(pyjitpl.MIFrame, 'opimpl_' + opname.lower()), opname

def test_faildescr_numbering():
    class FakeStaticData:
        state = None
        virtualizable_info = None

    fail_descr0 = AbstractFailDescr()
    lst = [fail_descr0]
    gd = pyjitpl.MetaInterpGlobalData(FakeStaticData, lst)
    assert gd.fail_descr_list is not lst

    fail_descr = gd.get_fail_descr_from_number(0)
    assert fail_descr is fail_descr0

    fail_descr1 = AbstractFailDescr()
    fail_descr2 = AbstractFailDescr()    

    n1 = gd.get_fail_descr_number(fail_descr1)
    n2 = gd.get_fail_descr_number(fail_descr2)
    assert n1 != n2

    fail_descr = gd.get_fail_descr_from_number(n1)
    assert fail_descr is fail_descr1
    fail_descr = gd.get_fail_descr_from_number(n2)
    assert fail_descr is fail_descr2

    # doesn't provide interning on its own
    n1_1 = gd.get_fail_descr_number(fail_descr1)
    assert n1_1 != n1
