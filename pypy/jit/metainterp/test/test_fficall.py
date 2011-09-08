
import py
from pypy.rlib.rarithmetic import r_singlefloat, r_longlong, r_ulonglong
from pypy.rlib.jit import JitDriver, promote, dont_look_inside
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.libffi import ArgChain, types
from pypy.rlib.libffi import IS_32_BIT, struct_setfield_int, struct_getfield_int
from pypy.rlib.test.test_libffi import TestLibffiCall as _TestLibffiCall
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import specialize
from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.metainterp.test.support import LLJitMixin

class TestFfiCall(LLJitMixin, _TestLibffiCall):
    supports_all = False     # supports_{floats,longlong,singlefloats}

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
            self.check_loops(
                call_release_gil=1,   # a CALL_RELEASE_GIL, and no other CALLs
                call=0,
                call_may_force=0,
                guard_no_exception=1,
                guard_not_forced=1,
                int_add=1,
                int_lt=1,
                guard_true=1,
                jump=1)
        else:
            self.check_loops(
                call_release_gil=0,   # no CALL_RELEASE_GIL
                int_add=1,
                int_lt=1,
                guard_true=1,
                jump=1)
        return res

    def test_byval_result(self):
        _TestLibffiCall.test_byval_result(self)
    test_byval_result.__doc__ = _TestLibffiCall.test_byval_result.__doc__
    test_byval_result.dont_track_allocations = True



class TestFfiCallSupportAll(TestFfiCall):
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
        self.check_loops(
            setfield_raw=1,
            getfield_raw=1,
            call=0)
        
