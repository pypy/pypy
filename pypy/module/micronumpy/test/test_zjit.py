""" Tests that check if JIT-compiled numpy operations produce reasonably
good assembler
"""

import py
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.metainterp.warmspot import reset_jit, get_stats
from pypy.module.micronumpy import boxes
from pypy.module.micronumpy.compile import FakeSpace, Parser, InterpreterState
from pypy.module.micronumpy.base import W_NDimArray


class TestNumpyJit(LLJitMixin):
    graph = None
    interp = None

    def setup_class(cls):
        default = """
        a = [1,2,3,4]
        z = (1, 2)
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

    def compile_graph(self):
        if self.graph is not None:
            return
        space = FakeSpace()
        codes = self.codes

        def f(i):
            interp = InterpreterState(codes[i])
            interp.run(space)
            if not len(interp.results):
                raise Exception("need results")
            w_res = interp.results[-1]
            if isinstance(w_res, W_NDimArray):
                w_res = w_res.create_iter().getitem()
            if isinstance(w_res, boxes.W_Float64Box):
                return w_res.value
            if isinstance(w_res, boxes.W_Int64Box):
                return float(w_res.value)
            elif isinstance(w_res, boxes.W_BoolBox):
                return float(w_res.value)
            raise TypeError(w_res)

        if self.graph is None:
            interp, graph = self.meta_interp(f, [0],
                                             listops=True,
                                             listcomp=True,
                                             backendopt=True,
                                             graph_and_interp_only=True)
            self.__class__.interp = interp
            self.__class__.graph = graph

    def run(self, name):
        self.compile_graph()
        reset_jit()
        i = self.code_mapping[name]
        retval = self.interp.eval_graph(self.graph, [i])
        return retval

    def define_add():
        return """
        a = |30|
        b = a + a
        b -> 3
        """

    def test_add(self):
        result = self.run("add")
        py.test.skip("don't run for now")
        self.check_simple_loop({'raw_load': 2, 'float_add': 1,
                                'raw_store': 1, 'int_add': 1,
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
        py.test.skip("don't run for now")
        self.check_simple_loop({"raw_load": 1, "float_add": 1,
                                "raw_store": 1, "int_add": 1,
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
        py.test.skip("don't run for now")
        self.check_simple_loop({"raw_load": 2, "float_add": 2,
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
        py.test.skip("don't run for now")
        # XXX note - the bridge here is fairly crucial and yet it's pretty
        #            bogus. We need to improve the situation somehow.
        self.check_simple_loop({'raw_load': 2,
                                'raw_store': 1,
                                'arraylen_gc': 2,
                                'guard_true': 1,
                                'int_lt': 1,
                                'jump': 1,
                                'float_add': 1,
                                'int_add': 3,
                                })

    def define_reduce():
        return """
        a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        sum(a)
        """

    def test_reduce_compile_only_once(self):
        self.compile_graph()
        reset_jit()
        i = self.code_mapping['reduce']
        # run it twice
        retval = self.interp.eval_graph(self.graph, [i])
        retval = self.interp.eval_graph(self.graph, [i])
        # check that we got only one loop
        assert len(get_stats().loops) == 1

    def test_reduce_axis_compile_only_once(self):
        self.compile_graph()
        reset_jit()
        i = self.code_mapping['axissum']
        # run it twice
        retval = self.interp.eval_graph(self.graph, [i])
        retval = self.interp.eval_graph(self.graph, [i])
        # check that we got only one loop
        assert len(get_stats().loops) == 1

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
        py.test.skip("don't run for now")
        self.check_simple_loop({"raw_load": 2, "float_add": 1,
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
        self.check_simple_loop({"raw_load": 2, "float_add": 1,
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
        self.check_simple_loop({"raw_load": 2, "float_add": 1,
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
        py.test.skip("don't run for now")
        self.check_simple_loop({"raw_load": 2, "float_add": 1,
                                "int_and": 1, "int_add": 1,
                                'cast_float_to_int': 1,
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
        self.check_resops({'raw_store': 4, 'getfield_gc': 22,
                           'getarrayitem_gc': 4, 'getarrayitem_gc_pure': 2,
                           'getfield_gc_pure': 8,
                           'guard_class': 8, 'int_add': 8, 'float_mul': 2,
                           'jump': 2, 'int_ge': 4,
                           'raw_load': 4, 'float_add': 2,
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
        py.test.skip("don't run for now")
        self.check_simple_loop({"raw_load": 2, "float_add": 1,
                                "float_neg": 1,
                                "raw_store": 1, "int_add": 1,
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
        py.test.skip("don't run for now")
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
        py.test.skip("don't run for now")
        self.check_simple_loop({'raw_load': 2,
                                'float_add': 1,
                                'raw_store': 1,
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
        skip('"take" not implmenented yet')
        result = self.run("take")
        assert result == 3
        self.check_simple_loop({'raw_load': 2,
                                'cast_float_to_int': 1,
                                'int_lt': 1,
                                'int_ge': 2,
                                'guard_false': 3,
                                'raw_store': 1,
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
        py.test.skip("don't run for now")
        # int_add might be 1 here if we try slightly harder with
        # reusing indexes or some optimization
        self.check_simple_loop({'float_add': 1, 'raw_load': 2,
                                'guard_false': 1, 'int_add': 1, 'int_ge': 1,
                                'jump': 1, 'raw_store': 1,
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
        py.test.skip("don't run for now")
        self.check_trace_count(1)
        self.check_simple_loop({'raw_load': 2, 'float_add': 1,
                                'raw_store': 1, 'int_add': 2,
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
        py.test.skip("don't run for now")
        self.check_trace_count(1)
        self.check_simple_loop({'raw_load': 2, 'float_add': 1,
                                'raw_store': 1, 'int_add': 1,
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
        py.test.skip("don't run for now")
        self.check_trace_count(1)
        self.check_simple_loop({'raw_load': 2, 'float_add': 1,
                                'raw_store': 1, 'int_add': 2,
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
        py.test.skip("don't run for now")
        self.check_trace_count(1)
        self.check_simple_loop({'raw_load': 1,
                                'raw_store': 1,
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
        py.test.skip("don't run for now")
        self.check_trace_count(1)
        # XXX not ideal, but hey, let's ignore it for now
        self.check_simple_loop({'raw_load': 1,
                                'raw_store': 1,
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
        self.check_simple_loop({'float_add': 1,
                                'float_mul': 1,
                                'guard_not_invalidated': 1,
                                'guard_true': 1,
                                'int_add': 3,
                                'int_lt': 1,
                                'jump': 1,
                                'raw_load': 2})
        self.check_resops({'arraylen_gc': 1,
                           'call': 3,
                           'float_add': 2,
                           'float_mul': 2,
                           'getfield_gc': 26,
                           'getfield_gc_pure': 24,
                           'guard_class': 4,
                           'guard_false': 2,
                           'guard_no_exception': 3,
                           'guard_nonnull': 8,
                           'guard_nonnull_class': 4,
                           'guard_not_invalidated': 2,
                           'guard_true': 9,
                           'guard_value': 4,
                           'int_add': 6,
                           'int_ge': 3,
                           'int_lt': 4,
                           'jump': 3,
                           'new_array': 1,
                           'raw_load': 6,
                           'raw_store': 1,
                           'setfield_gc': 3})

    def define_argsort():
        return """
        a = |30|
        argsort(a)
        a->6
        """

    def test_argsort(self):
        result = self.run("argsort")
        assert result == 6
