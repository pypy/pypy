import py
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rlib import jit
from pypy.rlib.jit_libffi import types, CIF_DESCRIPTION, FFI_TYPE_PP


def get_description(atypes, rtype):
    p = lltype.malloc(CIF_DESCRIPTION, len(atypes),
                      flavor='raw', immortal=True)
    rffi.setintfield(p, 'abi', 42)
    p.nargs = len(atypes)
    p.rtype = rtype
    p.atypes = lltype.malloc(FFI_TYPE_PP.TO, len(atypes),
                             flavor='raw', immortal=True)
    for i in range(len(atypes)):
        p.atypes[i] = atypes[i]
    return p

@jit.oopspec("libffi_call(cif_description, func_addr, exchange_buffer)")
def fake_call(cif_description, func_addr, exchange_buffer):
    assert rffi.cast(rffi.SIGNEDP, exchange_buffer)[0] == 456
    assert rffi.cast(rffi.SIGNEDP, exchange_buffer)[1] == 789
    rffi.cast(rffi.SIGNEDP, exchange_buffer)[2] = -42


class FfiCallTests(object):

    def test_call_simple(self):
        cif_description = get_description([types.signed]*2, types.signed)

        def verify(x, y):
            assert x == 456
            assert y == 789
            return -42
        FUNC = lltype.FuncType([lltype.Signed]*2, lltype.Signed)
        func = lltype.functionptr(FUNC, 'verify', _callable=verify)
        func_addr = rffi.cast(rffi.VOIDP, func)

        SIZE_SIGNED = rffi.sizeof(rffi.SIGNED)
        cif_description.exchange_args[1] = SIZE_SIGNED
        cif_description.exchange_result = 2 * SIZE_SIGNED

        def f(n, m):
            exbuf = lltype.malloc(rffi.CCHARP.TO, 24, flavor='raw', zero=True)
            rffi.cast(rffi.SIGNEDP, exbuf)[0] = n
            data = rffi.ptradd(exbuf, SIZE_SIGNED)
            rffi.cast(rffi.SIGNEDP, data)[0] = m
            fake_call(cif_description, func_addr, exbuf)
            data = rffi.ptradd(exbuf, 2 * SIZE_SIGNED)
            res = rffi.cast(rffi.SIGNEDP, data)[0]
            lltype.free(exbuf, flavor='raw')
            return res

        res = f(456, 789)
        assert res == -42
        res = self.interp_operations(f, [456, 789])
        assert res == -42
        self.check_operations_history(call_may_force=0,
                                      call_release_gil=1)


class TestFfiCall(FfiCallTests, LLJitMixin):
    pass
