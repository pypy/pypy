from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rpython.test.test_llinterp import interpret

from pypy.module.micronumpy.interp_numarray import (SingleDimArray, Signature,
    FloatWrapper, Call1, Call2, add, mul)
from pypy.module.micronumpy.interp_ufuncs import negative
from pypy.module.micronumpy.compile import numpy_compile

class FakeSpace(object):
    pass

class TestNumpyJIt(LLJitMixin):
    def setup_class(cls):
        cls.space = FakeSpace()

    def test_add(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i)
            v = Call2(add, ar, ar, Signature())
            return v.get_concrete().storage[3]

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_floatadd(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i)
            v = Call2(add, ar, FloatWrapper(4.5), Signature())
            return v.get_concrete().storage[3]

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 1, "float_add": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})
        assert result == f(5)

    def test_already_forecd(self):
        space = self.space

        def f(i):
            ar = SingleDimArray(i)
            v1 = Call2(add, ar, FloatWrapper(4.5), Signature())
            v2 = Call2(mul, v1, FloatWrapper(4.5), Signature())
            v1.force_if_needed()
            return v2.get_concrete().storage[3]

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        # This is the sum of the ops for both loops, however if you remove the
        # optimization then you end up with 2 float_adds, so we can still be
        # sure it was optimized correctly.
        self.check_loops({"getarrayitem_raw": 2, "float_mul": 1, "float_add": 1,
                           "setarrayitem_raw": 2, "int_add": 2,
                           "int_lt": 2, "guard_true": 2, "jump": 2})
        assert result == f(5)

    def test_ufunc(self):
        space = self.space
        def f(i):
            ar = SingleDimArray(i)
            v1 = Call2(add, ar, ar, Signature())
            v2 = negative(space, v1)
            return v2.get_concrete().storage[3]

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1, "float_neg": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1,
        })
        assert result == f(5)

    def test_appropriate_specialization(self):
        space = self.space
        def f(i):
            add_sig = Signature()
            mul_sig = Signature()
            ar = SingleDimArray(i)

            v1 = Call2(add, ar, ar, ar.signature.transition(add_sig))
            v2 = negative(space, v1)
            v2.get_concrete()

            for i in xrange(5):
                v1 = Call2(mul, ar, ar, ar.signature.transition(mul_sig))
                v2 = negative(space, v1)
                v2.get_concrete()

        self.meta_interp(f, [5], listops=True, backendopt=True)
        # This is 3, not 2 because there is a bridge for the exit.
        self.check_loop_count(3)

class TestTranslation(object):
    def test_compile(self):
        x = numpy_compile('aa+f*f/a-', 10)
        x = x.compute()
        assert isinstance(x, SingleDimArray)
        assert x.size == 10
        assert x.storage[0] == 0
        assert x.storage[1] == ((1 + 1) * 1.2) / 1.2 - 1
    
    def test_translation(self):
        # we import main to check if the target compiles
        from pypy.translator.goal.targetnumpystandalone import main
        from pypy.rpython.annlowlevel import llstr
        
        interpret(main, [llstr('af+'), 100])
