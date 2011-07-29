
import py
from pypy.rlib.rarithmetic import r_singlefloat, r_longlong, r_ulonglong
from pypy.rlib.jit import JitDriver, promote, dont_look_inside
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.libffi import ArgChain
from pypy.rlib.libffi import IS_32_BIT
from pypy.rlib.test.test_libffi import TestLibffiCall as _TestLibffiCall
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import specialize
from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.metainterp.test.support import LLJitMixin

class TestFfiCall(LLJitMixin, _TestLibffiCall):
    supports_all = False     # supports_{floats,longlong,singlefloats}

    # ===> ../../../rlib/test/test_libffi.py

    def check_loops_if_supported(self, *args, **kwds):
        if self.supports_all:
            self.check_loops(*args, **kwds)
        else:
            self.check_loops({'call': 1,
                              'guard_no_exception': 1,
                              'int_add': 1,
                              'int_lt': 1,
                              'guard_true': 1,
                              'jump': 1})

    def call(self, funcspec, args, RESULT, is_struct=False):
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
                               supports_singlefloats = False) # XXX self.supports_all)
        # the calls to check_loops() are in pypy.rlib.test.test_libffi
        return res

    def test_byval_result(self):
        _TestLibffiCall.test_byval_result(self)
    test_byval_result.__doc__ = _TestLibffiCall.test_byval_result.__doc__
    test_byval_result.dont_track_allocations = True


class TestFfiCallSupportAll(TestFfiCall):
    supports_all = True     # supports_{floats,longlong,singlefloats}
