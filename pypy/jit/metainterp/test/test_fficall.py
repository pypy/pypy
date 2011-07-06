
import py
from pypy.rlib.rarithmetic import r_singlefloat, r_longlong, r_ulonglong
from pypy.rlib.jit import JitDriver, promote, dont_look_inside
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.libffi import ArgChain, longlong2float, float2longlong
from pypy.rlib.libffi import IS_32_BIT
from pypy.rlib.test.test_libffi import TestLibffiCall as _TestLibffiCall
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import specialize
from pypy.tool.sourcetools import func_with_new_name
from pypy.jit.metainterp.test.support import LLJitMixin

class TestFfiCall(LLJitMixin, _TestLibffiCall):

    # ===> ../../../rlib/test/test_libffi.py

    def call(self, funcspec, args, RESULT, init_result=0, is_struct=False):
        """
        Call the function specified by funcspec in a loop, and let the jit to
        see and optimize it.
        """
        #
        lib, name, argtypes, restype = funcspec
        method_and_args = []
        for argval in args:
            if type(argval) is r_singlefloat:
                method_name = 'arg_singlefloat'
                argval = float(argval)
            elif IS_32_BIT and type(argval) in [r_longlong, r_ulonglong]:
                method_name = 'arg_longlong'
                argval = rffi.cast(rffi.LONGLONG, argval)
                argval = longlong2float(argval)
            elif isinstance(argval, tuple):
                method_name, argval = argval
            else:
                method_name = 'arg'
            method_and_args.append((method_name, argval))
        method_and_args = unrolling_iterable(method_and_args)
        #
        reds = ['n', 'res', 'func']
        if (RESULT in [rffi.FLOAT, rffi.DOUBLE] or
            IS_32_BIT and RESULT in [rffi.LONGLONG, rffi.ULONGLONG]):
            reds = ['n', 'func', 'res'] # floats must be *after* refs
        driver = JitDriver(reds=reds, greens=[])
        #
        def f(n):
            func = lib.getpointer(name, argtypes, restype)
            res = init_result
            while n < 10:
                driver.jit_merge_point(n=n, res=res, func=func)
                promote(func)
                argchain = ArgChain()
                # this loop is unrolled
                for method_name, argval in method_and_args:
                    getattr(argchain, method_name)(argval)
                res = func.call(argchain, RESULT, is_struct=is_struct)
                n += 1
            return res
        #
        res = self.meta_interp(f, [0], backendopt=True)
        return res

    def test_byval_result(self):
        _TestLibffiCall.test_byval_result(self)
    test_byval_result.__doc__ = _TestLibffiCall.test_byval_result.__doc__
    test_byval_result.dont_track_allocations = True
