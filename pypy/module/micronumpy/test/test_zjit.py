
""" Tests that check if JIT-compiled numpy operations produce reasonably
good assembler
"""

import py

from pypy.jit.metainterp import pyjitpl
from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.jit.metainterp.warmspot import reset_stats
from pypy.module.micronumpy import interp_boxes
from pypy.module.micronumpy.compile import (FakeSpace,
    IntObject, Parser, InterpreterState)
from pypy.module.micronumpy.interp_numarray import (W_NDimArray,
     BaseArray, W_FlatIterator)
from pypy.rlib.nonconst import NonConstant


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
            if not len(interp.results):
                raise Exception("need results")
            w_res = interp.results[-1]
            if isinstance(w_res, BaseArray):
                concr = w_res.get_concrete_or_scalar()
                sig = concr.find_sig()
                frame = sig.create_frame(concr)
                w_res = sig.eval(frame, concr)
            if isinstance(w_res, interp_boxes.W_Float64Box):
                return w_res.value
            if isinstance(w_res, interp_boxes.W_Int64Box):
                return float(w_res.value)
            elif isinstance(w_res, interp_boxes.W_BoolBox):
                return float(w_res.value)
            raise TypeError(w_res)

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
        self.check_simple_loop({'getinteriorfield_raw': 2, 'float_add': 1,
                                'setinteriorfield_raw': 1, 'int_add': 2,
                                'int_ge': 1, 'guard_false': 1, 'jump': 1,
                                'arraylen_gc': 1})
        assert result == 3 + 3

    def define_float_add():
        return """
        a = |30| + 3
        a -> 3
        """

    def test_floatadd(self):
        result = self.run("float_add")
        assert result == 3 + 3
        self.check_simple_loop({"getinteriorfield_raw": 1, "float_add": 1,
                                "setinteriorfield_raw": 1, "int_add": 2,
                                "int_ge": 1, "guard_false": 1, "jump": 1,
                                'arraylen_gc': 1})

    def define_sum():
        return """
        a = |30|
        b = a + a
        sum(b)
        """

    def test_sum(self):
        result = self.run("sum")
        assert result == 2 * sum(range(30))
        self.check_simple_loop({"getinteriorfield_raw": 2, "float_add": 2,
                                "int_add": 1, "int_ge": 1, "guard_false": 1,
                                "jump": 1, 'arraylen_gc': 1})

    def define_axissum():
        return """
        a = [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]
        b = sum(a,0)
        b -> 1
        """

    def test_axissum(self):
        result = self.run("axissum")
        assert result == 30
        # XXX note - the bridge here is fairly crucial and yet it's pretty
        #            bogus. We need to improve the situation somehow.
        self.check_simple_loop({'getinteriorfield_raw': 2,
                                'setinteriorfield_raw': 1,
                                'arraylen_gc': 1,
                                'guard_true': 1,
                                'int_lt': 1,
                                'jump': 1,
                                'float_add': 1,
                                'int_add': 3,
                                })

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
        self.check_simple_loop({"getinteriorfield_raw": 2, "float_add": 1,
                                "float_mul": 1, "int_add": 1,
                                "int_ge": 1, "guard_false": 1, "jump": 1,
                                'arraylen_gc': 1})

    def define_max():
        return """
        a = |30|
        a[13] = 128
        b = a + a
        max(b)
        """

    def test_max(self):
        result = self.run("max")
        assert result == 256
        py.test.skip("not there yet, getting though")
        self.check_simple_loop({"getinteriorfield_raw": 2, "float_add": 1,
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
        self.check_simple_loop({"getinteriorfield_raw": 2, "float_add": 1,
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
        self.check_simple_loop({"getinteriorfield_raw": 2, "float_add": 1,
                                "float_ne": 1, "int_add": 1,
                                "int_ge": 1, "jump": 1,
                                "guard_false": 2, 'arraylen_gc': 1})

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
        py.test.skip("too fragile")
        self.check_resops({'setinteriorfield_raw': 4, 'getfield_gc': 22,
                           'getarrayitem_gc': 4, 'getarrayitem_gc_pure': 2,
                           'getfield_gc_pure': 8,
                           'guard_class': 8, 'int_add': 8, 'float_mul': 2,
                           'jump': 2, 'int_ge': 4,
                           'getinteriorfield_raw': 4, 'float_add': 2,
                           'guard_false': 4, 'arraylen_gc': 2, 'same_as': 2})

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
        self.check_simple_loop({"getinteriorfield_raw": 2, "float_add": 1,
                                "float_neg": 1,
                                "setinteriorfield_raw": 1, "int_add": 2,
                                "int_ge": 1, "guard_false": 1, "jump": 1,
                                'arraylen_gc': 1})

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
        self.check_trace_count(3)

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
        self.check_simple_loop({'getinteriorfield_raw': 2,
                                'float_add': 1,
                                'setinteriorfield_raw': 1,
                                'int_add': 3,
                                'int_ge': 1, 'guard_false': 1,
                                'jump': 1,
                                'arraylen_gc': 1})

    def define_take():
        return """
        a = |10|
        b = take(a, [1, 1, 3, 2])
        b -> 2
        """

    def test_take(self):
        result = self.run("take")
        assert result == 3
        self.check_simple_loop({'getinteriorfield_raw': 2,
                                'cast_float_to_int': 1,
                                'int_lt': 1,
                                'int_ge': 2,
                                'guard_false': 3,
                                'setinteriorfield_raw': 1,
                                'int_mul': 1,
                                'int_add': 3,
                                'jump': 1,
                                'arraylen_gc': 2})

    def define_multidim():
        return """
        a = [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]
        b = a + a
        b -> 1 -> 1
        """

    def test_multidim(self):
        result = self.run('multidim')
        assert result == 8
        # int_add might be 1 here if we try slightly harder with
        # reusing indexes or some optimization
        self.check_simple_loop({'float_add': 1, 'getinteriorfield_raw': 2,
                                'guard_false': 1, 'int_add': 2, 'int_ge': 1,
                                'jump': 1, 'setinteriorfield_raw': 1,
                                'arraylen_gc': 1})

    def define_multidim_slice():
        return """
        a = [[1, 2, 3, 4], [3, 4, 5, 6], [5, 6, 7, 8], [7, 8, 9, 10], [9, 10, 11, 12], [11, 12, 13, 14], [13, 14, 15, 16], [16, 17, 18, 19]]
        b = a -> ::2
        c = b + b
        c -> 1 -> 1
        """

    def test_multidim_slice(self):
        result = self.run('multidim_slice')
        assert result == 12
        py.test.skip("improve")
        # XXX the bridge here is scary. Hopefully jit-targets will fix that,
        #     otherwise it looks kind of good
        self.check_simple_loop({})

    def define_broadcast():
        return """
        a = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
        b = [1, 2, 3, 4]
        c = a + b
        c -> 1 -> 2
        """

    def test_broadcast(self):
        result = self.run("broadcast")
        assert result == 10
        py.test.skip("improve")
        self.check_simple_loop({})

    def define_setslice():
        return """
        a = |30|
        b = |10|
        b[1] = 5.5
        c = b + b
        a[0:30:3] = c
        a -> 3
        """

    def test_setslice(self):
        result = self.run("setslice")
        assert result == 11.0
        self.check_trace_count(1)
        self.check_simple_loop({'getinteriorfield_raw': 2, 'float_add': 1,
                                'setinteriorfield_raw': 1, 'int_add': 2,
                                'int_eq': 1, 'guard_false': 1, 'jump': 1,
                                'arraylen_gc': 1})

    def define_virtual_slice():
        return """
        a = |30|
        c = a + a
        d = c -> 1:20
        d -> 1
        """

    def test_virtual_slice(self):
        result = self.run("virtual_slice")
        assert result == 4
        self.check_trace_count(1)
        self.check_simple_loop({'getinteriorfield_raw': 2, 'float_add': 1,
                                'setinteriorfield_raw': 1, 'int_add': 2,
                                'int_ge': 1, 'guard_false': 1, 'jump': 1,
                                'arraylen_gc': 1})
    def define_flat_iter():
        return '''
        a = |30|
        b = flat(a)
        c = b + a
        c -> 3
        '''

    def test_flat_iter(self):
        result = self.run("flat_iter")
        assert result == 6
        self.check_trace_count(1)
        self.check_simple_loop({'getinteriorfield_raw': 2, 'float_add': 1,
                                'setinteriorfield_raw': 1, 'int_add': 3,
                                'int_ge': 1, 'guard_false': 1,
                                'arraylen_gc': 1, 'jump': 1})

    def define_flat_getitem():
        return '''
        a = |30|
        b = flat(a)
        b -> 4: -> 6
        '''

    def test_flat_getitem(self):
        result = self.run("flat_getitem")
        assert result == 10.0
        self.check_trace_count(1)
        self.check_simple_loop({'getinteriorfield_raw': 1,
                                'setinteriorfield_raw': 1,
                                'int_lt': 1,
                                'int_ge': 1,
                                'int_add': 3,
                                'guard_true': 1,
                                'guard_false': 1,
                                'arraylen_gc': 2,
                                'jump': 1})

    def define_flat_setitem():
        return '''
        a = |30|
        b = flat(a)
        b[4:] = a->:26
        a -> 5
        '''

    def test_flat_setitem(self):
        result = self.run("flat_setitem")
        assert result == 1.0
        self.check_trace_count(1)
        # XXX not ideal, but hey, let's ignore it for now
        self.check_simple_loop({'getinteriorfield_raw': 1,
                                'setinteriorfield_raw': 1,
                                'int_lt': 1,
                                'int_gt': 1,
                                'int_add': 4,
                                'guard_true': 2,
                                'arraylen_gc': 2,
                                'jump': 1,
                                'int_sub': 1,
                                # XXX bad part
                                'int_and': 1,
                                'int_mod': 1,
                                'int_rshift': 1,
                                })

    def define_dot():
        return """
        a = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
        b=[[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]
        c = dot(a, b)
        c -> 1 -> 2
        """

    def test_dot(self):
        result = self.run("dot")
        assert result == 184
        self.check_simple_loop({{'arraylen_gc': 9,
                                'float_add': 1,
                                'float_mul': 1,
                                'getinteriorfield_raw': 3,
                                'guard_false': 3,
                                'guard_true': 3,
                                'int_add': 6,
                                'int_lt': 6,
                                'int_sub': 3,
                                'jump': 1,
                                'setinteriorfield_raw': 1}})


class TestNumpyOld(LLJitMixin):
    def setup_class(cls):
        py.test.skip("old")
        from pypy.module.micronumpy.compile import FakeSpace
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache

        cls.space = FakeSpace()
        cls.float64_dtype = get_dtype_cache(cls.space).w_float64dtype

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
            ar = W_NDimArray(n, [n], dtype=dtype)
            i = 0
            while i < n:
                ar.get_concrete().setitem(i, int32_dtype.box(7))
                i += 1
            v = ar.descr_add(space, ar).descr_sum(space)
            assert isinstance(v, IntObject)
            return v.intval

        result = self.meta_interp(f, [5], listops=True, backendopt=True)
        assert result == f(5)
