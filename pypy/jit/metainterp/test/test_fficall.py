from __future__ import with_statement
import py

from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rlib.jit import JitDriver, promote, dont_look_inside
from pypy.rlib.libffi import (ArgChain, IS_32_BIT, array_getitem, array_setitem,
    types, struct_setfield_int, struct_getfield_int)
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import r_singlefloat, r_longlong, r_ulonglong
from pypy.rlib.test.test_libffi import TestLibffiCall as _TestLibffiCall
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.tool.sourcetools import func_with_new_name


class FfiCallTests(_TestLibffiCall):
    # ===> ../../../rlib/test/test_libffi.py

    def call(self, funcspec, args, RESULT, is_struct=False, jitif=[]):
        """
        Call the function specified by funcspec in a loop, and let the jit to
        see and optimize it.
        """
        #
        lib, name, argtypes, restype = funcspec
        method_and_args = []
        for argval in args:
            if isinstance(argval, tuple):
                method_name, argval = argval
            else:
                method_name = 'arg'
            method_and_args.append((method_name, argval))
        method_and_args = unrolling_iterable(method_and_args)
        #
        reds = ['n', 'res', 'func']
        if (RESULT is rffi.DOUBLE or
            IS_32_BIT and RESULT in [rffi.LONGLONG, rffi.ULONGLONG]):
            reds = ['n', 'func', 'res'] # 'double' floats must be *after* refs
        driver = JitDriver(reds=reds, greens=[])
        init_result = rffi.cast(RESULT, 0)
        #
        def g(func):
            # a different function, which is marked as "dont_look_inside"
            # in case it uses an unsupported argument
            argchain = ArgChain()
            # this loop is unrolled
            for method_name, argval in method_and_args:
                getattr(argchain, method_name)(argval)
            return func.call(argchain, RESULT, is_struct=is_struct)
        #
        def f(n):
            func = lib.getpointer(name, argtypes, restype)
            res = init_result
            while n < 10:
                driver.jit_merge_point(n=n, res=res, func=func)
                promote(func)
                res = g(func)
                n += 1
            return res
        #
        res = self.meta_interp(f, [0], backendopt=True,
                               supports_floats       = self.supports_all,
                               supports_longlong     = self.supports_all,
                               supports_singlefloats = self.supports_all)
        d = {'floats': self.supports_all,
             'longlong': self.supports_all or not IS_32_BIT,
             'singlefloats': self.supports_all,
             'byval': False}
        supported = all(d[check] for check in jitif)
        if supported:
            self.check_resops(
                call_release_gil=2,   # a CALL_RELEASE_GIL, and no other CALLs
                call=0,
                call_may_force=0,
                guard_no_exception=2,
                guard_not_forced=2,
                int_add=2,
                int_lt=2,
                guard_true=2,
                jump=1)
        else:
            self.check_resops(
                call_release_gil=0,   # no CALL_RELEASE_GIL
                int_add=2,
                int_lt=2,
                guard_true=2,
                jump=1)
        return res

    def test_byval_result(self):
        _TestLibffiCall.test_byval_result(self)
    test_byval_result.__doc__ = _TestLibffiCall.test_byval_result.__doc__
    test_byval_result.dont_track_allocations = True

class FfiLookupTests(object):
    def test_array_fields(self):
        myjitdriver = JitDriver(
            greens = [],
            reds = ["n", "i", "points", "result_point"],
        )

        POINT = lltype.Struct("POINT",
            ("x", lltype.Signed),
            ("y", lltype.Signed),
        )
        def f(points, result_point, n):
            i = 0
            while i < n:
                myjitdriver.jit_merge_point(i=i, points=points, n=n,
                                            result_point=result_point)
                x = array_getitem(
                    types.slong, rffi.sizeof(lltype.Signed) * 2, points, i, 0
                )
                y = array_getitem(
                    types.slong, rffi.sizeof(lltype.Signed) * 2, points, i, rffi.sizeof(lltype.Signed)
                )

                cur_x = array_getitem(
                    types.slong, rffi.sizeof(lltype.Signed) * 2, result_point, 0, 0
                )
                cur_y = array_getitem(
                    types.slong, rffi.sizeof(lltype.Signed) * 2, result_point, 0, rffi.sizeof(lltype.Signed)
                )

                array_setitem(
                    types.slong, rffi.sizeof(lltype.Signed) * 2, result_point, 0, 0, cur_x + x
                )
                array_setitem(
                    types.slong, rffi.sizeof(lltype.Signed) * 2, result_point, 0, rffi.sizeof(lltype.Signed), cur_y + y
                )
                i += 1

        def main(n):
            with lltype.scoped_alloc(rffi.CArray(POINT), n) as points:
                with lltype.scoped_alloc(rffi.CArray(POINT), 1) as result_point:
                    for i in xrange(n):
                        points[i].x = i * 2
                        points[i].y = i * 2 + 1
                    points = rffi.cast(rffi.CArrayPtr(lltype.Char), points)
                    result_point[0].x = 0
                    result_point[0].y = 0
                    result_point = rffi.cast(rffi.CArrayPtr(lltype.Char), result_point)
                    f(points, result_point, n)
                    result_point = rffi.cast(rffi.CArrayPtr(POINT), result_point)
                    return result_point[0].x * result_point[0].y

        assert self.meta_interp(main, [10]) == main(10) == 9000
        self.check_resops({'jump': 1, 'int_lt': 2, 'setinteriorfield_raw': 4,
                           'getinteriorfield_raw': 8, 'int_add': 6, 'guard_true': 2})

    def _test_getitem_type(self, TYPE, ffitype, COMPUTE_TYPE):
        reds = ["n", "i", "s", "data"]
        if COMPUTE_TYPE is lltype.Float:
            # Move the float var to the back.
            reds.remove("s")
            reds.append("s")
        myjitdriver = JitDriver(
            greens = [],
            reds = reds,
        )
        def f(data, n):
            i = 0
            s = rffi.cast(COMPUTE_TYPE, 0)
            while i < n:
                myjitdriver.jit_merge_point(n=n, i=i, s=s, data=data)
                s += rffi.cast(COMPUTE_TYPE, array_getitem(ffitype, rffi.sizeof(TYPE), data, 0, 0))
                i += 1
            return s
        def main(n):
            with lltype.scoped_alloc(rffi.CArray(TYPE), 1) as data:
                data[0] = rffi.cast(TYPE, 200)
                return f(data, n)
        assert self.meta_interp(main, [10]) == 2000

    def test_array_getitem_uint8(self):
        self._test_getitem_type(rffi.UCHAR, types.uchar, lltype.Signed)
        self.check_resops({'jump': 1, 'int_lt': 2, 'getinteriorfield_raw': 2,
                           'guard_true': 2, 'int_add': 4})

    def test_array_getitem_float(self):
        self._test_getitem_type(rffi.FLOAT, types.float, lltype.Float)


class TestFfiCall(FfiCallTests, LLJitMixin):
    supports_all = False

class TestFfiCallSupportAll(FfiCallTests, LLJitMixin):
    supports_all = True     # supports_{floats,longlong,singlefloats}

    def test_struct_getfield(self):
        myjitdriver = JitDriver(greens = [], reds = ['n', 'i', 'addr'])

        def f(n):
            i = 0
            addr = lltype.malloc(rffi.VOIDP.TO, 10, flavor='raw')
            while i < n:
                myjitdriver.jit_merge_point(n=n, i=i, addr=addr)
                struct_setfield_int(types.slong, addr, 0, 1)
                i += struct_getfield_int(types.slong, addr, 0)
            lltype.free(addr, flavor='raw')
            return i
        assert self.meta_interp(f, [20]) == f(20)
        self.check_resops(
            setfield_raw=2,
            getfield_raw=2,
            call=0)


class TestFfiLookup(FfiLookupTests, LLJitMixin):
    pass
