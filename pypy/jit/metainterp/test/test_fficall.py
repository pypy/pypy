
import py
from pypy.rlib.jit import JitDriver, hint
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.libffi import ArgChain
from pypy.rlib.test.test_libffi import TestLibffiCall as _TestLibffiCall
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.metainterp.test.support import LLJitMixin


class TestFfiCall(LLJitMixin, _TestLibffiCall):

    # ===> ../../../rlib/test/test_libffi.py

    def call(self, funcspec, args, RESULT, init_result=0):
        """
        Call the function specified by funcspec in a loop, and let the jit to
        see and optimize it.
        """
        #
        lib, name, argtypes, restype = funcspec
        args = unrolling_iterable(args)
        #
        reds = ['n', 'res', 'func']
        if type(init_result) is float:
            reds = ['n', 'func', 'res'] # floats must be *after* refs
        driver = JitDriver(reds=reds, greens=[])
        #
        def f(n):
            func = lib.getpointer(name, argtypes, restype)
            res = init_result
            while n < 10:
                driver.jit_merge_point(n=n, res=res, func=func)
                driver.can_enter_jit(n=n, res=res, func=func)
                func = hint(func, promote=True)
                argchain = ArgChain()
                for argval in args: # this loop is unrolled
                    argchain.arg(argval)
                res = func.call(argchain, RESULT)
                n += 1
            return res
        #
        res = self.meta_interp(f, [0])
        return res

