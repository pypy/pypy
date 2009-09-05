
# some unit tests for the bytecode decoding

from pypy.jit.metainterp import pyjitpl, codewriter, resoperation

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
