
""" Tests that check if JIT-compiled numpy operations produce reasonably
good assembler
"""


import py
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.module.micronumpy import interp_ufuncs, signature
from pypy.module.micronumpy.compile import (numpy_compile, FakeSpace,
    FloatObject, IntObject, BoolObject, Parser, InterpreterState)
from pypy.module.micronumpy.interp_numarray import NDimArray, NDimSlice
from pypy.rlib.nonconst import NonConstant
from pypy.rpython.annlowlevel import llstr, hlstr
from pypy.jit.metainterp.warmspot import reset_stats
from pypy.jit.metainterp import pyjitpl

class TestNumpyJIt(LLJitMixin):
    graph = None
    interp = None

    def setup_class(cls):
        default = """
        a = [1,2,3,4]
        c = a + b
        sum(c) -> 1::1
        a -> 3:1:2
        """

        d = {}
        p = Parser()
        allcodes = [p.parse(default)]
        for name, meth in cls.__dict__.iteritems():
            if name.startswith("define_"):
                code = meth()
                d[name[len("define_"):]] = len(allcodes)
                allcodes.append(p.parse(code))
        cls.code_mapping = d
        cls.codes = allcodes
        
    def run(self, name):
        space = FakeSpace()
        i = self.code_mapping[name]
        codes = self.codes
        
        def f(i):
            interp = InterpreterState(codes[i])
            interp.run(space)
            res = interp.results[-1]
            w_res = res.eval(res.start_iter()).wrap(interp.space)
            if isinstance(w_res, BoolObject):
                return float(w_res.boolval)
            elif isinstance(w_res, FloatObject):
                return w_res.floatval
            elif isinstance(w_res, IntObject):
                return w_res.intval
            else:
                return -42.

        if self.graph is None:
            interp, graph = self.meta_interp(f, [i],
                                             listops=True,
                                             backendopt=True,
                                             graph_and_interp_only=True)
            self.__class__.interp = interp
            self.__class__.graph = graph
        reset_stats()
        pyjitpl._warmrunnerdesc.memory_manager.alive_loops.clear()
        return self.interp.eval_graph(self.graph, [i])

    def define_add():
        return """
        a = |30|
        b = a + a
        b -> 3
        """

    def test_add(self):
        result = self.run("add")
        self.check_loops({'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == 3 + 3

    def define_float_add():
        return """
        a = |30| + 3
        a -> 3
        """

    def test_floatadd(self):
        result = self.run("float_add")
        assert result == 3 + 3
        self.check_loops({"getarrayitem_raw": 1, "float_add": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def define_sum():
        return """
        a = |30|
        b = a + a
        sum(b)
        """

    def test_sum(self):
        result = self.run("sum")
        assert result == 2 * sum(range(30))
        self.check_loops({"getarrayitem_raw": 2, "float_add": 2,
                          "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def define_prod():
        return """
        a = |30|
        b = a + a
        prod(b)
        """

    def test_prod(self):
        result = self.run("prod")
        expected = 1
        for i in range(30):
            expected *= i * 2
        assert result == expected
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_max(self):
        py.test.skip("broken, investigate")
        result = self.run("""
        a = |30|
        a[13] = 128
        b = a + a
        max(b)
        """)
        assert result == 256
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def test_min(self):
        py.test.skip("broken, investigate")
        result = self.run("""
        a = |30|
        a[15] = -12
        b = a + a
        min(b)
        """)
        assert result == -24
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_mul": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1})

    def define_any():
        return """
        a = [0,0,0,0,0,0,0,0,0,0,0]
        a[8] = -12
        b = a + a
        any(b)
        """

    def test_any(self):
        result = self.run("any")
        assert result == 1
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1,
                          "float_ne": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1,
                          "guard_false": 1})

    def define_already_forced():
        return """
        a = |30|
        b = a + 4.5
        b -> 5 # forces
        c = b * 8
        c -> 5
        """

    def test_already_forced(self):
        result = self.run("already_forced")
        assert result == (5 + 4.5) * 8
        # This is the sum of the ops for both loops, however if you remove the
        # optimization then you end up with 2 float_adds, so we can still be
        # sure it was optimized correctly.
        self.check_loops({"getarrayitem_raw": 2, "float_mul": 1, "float_add": 1,
                           "setarrayitem_raw": 2, "int_add": 2,
                           "int_lt": 2, "guard_true": 2, "jump": 2})

    def define_ufunc():
        return """
        a = |30|
        b = a + a
        c = unegative(b)
        c -> 3
        """

    def test_ufunc(self):
        result = self.run("ufunc")
        assert result == -6
        self.check_loops({"getarrayitem_raw": 2, "float_add": 1, "float_neg": 1,
                          "setarrayitem_raw": 1, "int_add": 1,
                          "int_lt": 1, "guard_true": 1, "jump": 1,
        })

    def define_specialization():
        return """
        a = |30|
        b = a + a
        c = unegative(b)
        c -> 3
        d = a * a
        unegative(d)
        d -> 3
        d = a * a
        unegative(d)
        d -> 3
        d = a * a
        unegative(d)
        d -> 3
        d = a * a
        unegative(d)
        d -> 3
        """

    def test_specialization(self):
        self.run("specialization")
        # This is 3, not 2 because there is a bridge for the exit.
        self.check_loop_count(3)

    def define_slice():
        return """
        a = |30|
        b = a -> ::3
        c = b + b
        c -> 3
        """

    def test_slice(self):
        result = self.run("slice")
        assert result == 18
        self.check_loops({'int_mul': 2, 'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 3,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})

    def define_multidim():
        return """
        a = [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]
        b = a + a
        b -> 1 -> 1
        """

    def test_multidim(self):
        result = self.run('multidim')
        assert result == 8
        self.check_loops({'float_add': 1, 'getarrayitem_raw': 2,
                          'guard_false': 1, 'int_add': 3, 'int_ge': 1,
                          'jump': 1, 'setarrayitem_raw': 1})
        # int_add might be 1 here if we try slightly harder with
        # reusing indexes or some optimization

    def define_multidim_slice():
        return """
        a = [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14]]
        b = a -> ::2
        c = b + b
        c -> 1 -> 1
        """

    def test_multidim_slice(self):
        result = self.run('multidim_slice')
        assert result == 12
        py.test.skip("improve")
        self.check_loops({})
    

class TestNumpyOld(LLJitMixin):
    def setup_class(cls):
        py.test.skip("old")
        from pypy.module.micronumpy.compile import FakeSpace
        from pypy.module.micronumpy.interp_dtype import W_Float64Dtype
        
        cls.space = FakeSpace()
        cls.float64_dtype = cls.space.fromcache(W_Float64Dtype)
    
    def test_slice2(self):
        def f(i):
            step1 = 2
            step2 = 3
            ar = NDimArray(step2*i, dtype=self.float64_dtype)
            new_sig = signature.Signature.find_sig([
                NDimSlice.signature, ar.signature
            ])
            s1 = NDimSlice(0, step1*i, step1, i, ar, new_sig)
            new_sig = signature.Signature.find_sig([
                NDimSlice.signature, s1.signature
            ])
            s2 = NDimSlice(0, step2*i, step2, i, ar, new_sig)
            v = interp_ufuncs.get(self.space).add.call(self.space, [s1, s2])
            return v.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'int_mul': 2, 'getarrayitem_raw': 2, 'float_add': 1,
                          'setarrayitem_raw': 1, 'int_add': 1,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == f(5)

    def test_setslice(self):
        space = self.space
        float64_dtype = self.float64_dtype

        def f(i):
            step = NonConstant(3)
            ar = NDimArray(step*i, dtype=float64_dtype)
            ar2 = NDimArray(i, dtype=float64_dtype)
            ar2.get_concrete().setitem(1, float64_dtype.box(5.5))
            arg = ar2.descr_add(space, ar2)
            ar.setslice(space, 0, step*i, step, i, arg)
            return ar.get_concrete().eval(3).val

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        self.check_loops({'getarrayitem_raw': 2,
                          'float_add' : 1,
                          'setarrayitem_raw': 1, 'int_add': 2,
                          'int_lt': 1, 'guard_true': 1, 'jump': 1})
        assert result == 11.0

    def test_int32_sum(self):
        py.test.skip("pypy/jit/backend/llimpl.py needs to be changed to "
                     "deal correctly with int dtypes for this test to "
                     "work. skip for now until someone feels up to the task")
        space = self.space
        float64_dtype = self.float64_dtype
        int32_dtype = self.int32_dtype

        def f(n):
            if NonConstant(False):
                dtype = float64_dtype
            else:
                dtype = int32_dtype
            ar = NDimArray(n, [n], dtype=dtype)
            i = 0
            while i < n:
                ar.get_concrete().setitem(i, int32_dtype.box(7))
                i += 1
            v = ar.descr_add(space, ar).descr_sum(space)
            assert isinstance(v, IntObject)
            return v.intval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        assert result == f(5)

