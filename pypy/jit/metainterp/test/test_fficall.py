
import ctypes, math
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rlib import jit
from pypy.rlib.jit_libffi import types, CIF_DESCRIPTION, FFI_TYPE_PP
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import intmask


def get_description(atypes, rtype):
    p = lltype.malloc(CIF_DESCRIPTION, len(atypes),
                      flavor='raw', immortal=True)
    p.abi = 42
    p.nargs = len(atypes)
    p.rtype = rtype
    p.atypes = lltype.malloc(FFI_TYPE_PP.TO, len(atypes),
                             flavor='raw', immortal=True)
    for i in range(len(atypes)):
        p.atypes[i] = atypes[i]
    return p


class FfiCallTests(object):

    def _run(self, atypes, rtype, avalues, rvalue):
        cif_description = get_description(atypes, rtype)

        def verify(*args):
            assert args == tuple(avalues)
            return rvalue
        FUNC = lltype.FuncType([lltype.typeOf(avalue) for avalue in avalues],
                               lltype.typeOf(rvalue))
        func = lltype.functionptr(FUNC, 'verify', _callable=verify)
        func_addr = rffi.cast(rffi.VOIDP, func)

        for i in range(len(avalues)):
            cif_description.exchange_args[i] = (i+1) * 16
        cif_description.exchange_result = (len(avalues)+1) * 16

        unroll_avalues = unrolling_iterable(avalues)

        @jit.oopspec("libffi_call(cif_description,func_addr,exchange_buffer)")
        def fake_call(cif_description, func_addr, exchange_buffer):
            ofs = 16
            for avalue in unroll_avalues:
                TYPE = rffi.CArray(lltype.typeOf(avalue))
                data = rffi.ptradd(exchange_buffer, ofs)
                assert rffi.cast(lltype.Ptr(TYPE), data)[0] == avalue
                ofs += 16
            if rvalue is not None:
                write_rvalue = rvalue
            else:
                write_rvalue = 12923  # ignored
            TYPE = rffi.CArray(lltype.typeOf(write_rvalue))
            data = rffi.ptradd(exchange_buffer, ofs)
            rffi.cast(lltype.Ptr(TYPE), data)[0] = write_rvalue

        def f():
            exbuf = lltype.malloc(rffi.CCHARP.TO, (len(avalues)+2) * 16,
                                  flavor='raw', zero=True)
            ofs = 16
            for avalue in unroll_avalues:
                TYPE = rffi.CArray(lltype.typeOf(avalue))
                data = rffi.ptradd(exbuf, ofs)
                rffi.cast(lltype.Ptr(TYPE), data)[0] = avalue
                ofs += 16

            fake_call(cif_description, func_addr, exbuf)

            if rvalue is None:
                res = 654321
            else:
                TYPE = rffi.CArray(lltype.typeOf(rvalue))
                data = rffi.ptradd(exbuf, ofs)
                res = rffi.cast(lltype.Ptr(TYPE), data)[0]
            lltype.free(exbuf, flavor='raw')
            return res

        res = f()
        assert res == rvalue or (res, rvalue) == (654321, None)
        res = self.interp_operations(f, [])
        assert res == rvalue or (res, rvalue) == (654321, None)
        self.check_operations_history(call_may_force=0,
                                      call_release_gil=1)

    def test_simple_call(self):
        self._run([types.signed] * 2, types.signed, [456, 789], -42)

    def test_many_arguments(self):
        for i in [0, 6, 20]:
            self._run([types.signed] * i, types.signed,
                      [-123456*j for j in range(i)],
                      -42434445)

    def test_simple_call_float(self):
        self._run([types.double] * 2, types.double, [45.6, 78.9], -4.2)

    def test_returns_none(self):
        self._run([types.signed] * 2, types.void, [456, 789], None)

    def test_returns_signedchar(self):
        self._run([types.signed], types.sint8, [456],
                  rffi.cast(rffi.SIGNEDCHAR, -42))


class TestFfiCall(FfiCallTests, LLJitMixin):
    def test_jit_fii_vref(self):
        from pypy.rlib import clibffi
        from pypy.rlib.jit_libffi import jit_ffi_prep_cif, jit_ffi_call

        math_sin = intmask(ctypes.cast(ctypes.CDLL(None).sin,
                                       ctypes.c_void_p).value)
        math_sin = rffi.cast(rffi.VOIDP, math_sin)

        cd = lltype.malloc(CIF_DESCRIPTION, 1, flavor='raw')
        cd.abi = clibffi.FFI_DEFAULT_ABI
        cd.nargs = 1
        cd.rtype = clibffi.cast_type_to_ffitype(rffi.DOUBLE)
        atypes = lltype.malloc(clibffi.FFI_TYPE_PP.TO, 1, flavor='raw')
        atypes[0] = clibffi.cast_type_to_ffitype(rffi.DOUBLE)
        cd.atypes = atypes
        cd.exchange_size = 64    # 64 bytes of exchange data
        cd.exchange_result = 24
        cd.exchange_result_libffi = 24
        cd.exchange_args[0] = 16

        def f():
            #
            jit_ffi_prep_cif(cd)
            #
            assert rffi.sizeof(rffi.DOUBLE) == 8
            exb = lltype.malloc(rffi.DOUBLEP.TO, 8, flavor='raw')
            exb[2] = 1.23
            jit_ffi_call(cd, math_sin, rffi.cast(rffi.CCHARP, exb))
            res = exb[3]
            lltype.free(exb, flavor='raw')
            #
            lltype.free(atypes, flavor='raw')
            return res
            #
        res = self.interp_operations(f, [])
        lltype.free(cd, flavor='raw')
        assert res == math.sin(1.23)
