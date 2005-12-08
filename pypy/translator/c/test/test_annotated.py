import autopath
import py, sys
from pypy.translator.tool.cbuild import skip_missing_compiler
from pypy.translator.translator import TranslationContext

from pypy.translator.test import snippet 

# XXX this tries to make compiling faster for full-scale testing
from pypy.translator.tool import cbuild
cbuild.enable_fast_compilation()

class TestAnnotatedTestCase:

    def annotatefunc(self, func):
        t = TranslationContext(simplifying=True)
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        a = t.buildannotator()
        a.build_types(func, argstypelist)
        a.simplify()
        return t

    def compilefunc(self, t, func):
        from pypy.translator.c import genc
        builder = genc.CExtModuleBuilder(t, func)
        builder.generate_source()
        skip_missing_compiler(builder.compile)
        builder.import_module()
        return builder.get_entry_point()

    def process(self, t):
        pass

    def getcompiled(self, func, view=False):
        t = self.annotatefunc(func)
        self.process(t)
        if view:
            t.view()
        t.checkgraphs()
        return self.compilefunc(t, func)

    def test_set_attr(self):
        set_attr = self.getcompiled(snippet.set_attr)
        assert set_attr() == 2

    def test_inheritance2(self):
        inheritance2 = self.getcompiled(snippet.inheritance2)
        assert inheritance2() == ((-12, -12), (3, "world"))

    def test_factorial2(self):
        factorial2 = self.getcompiled(snippet.factorial2)
        assert factorial2(5) == 120

    def test_factorial(self):
        factorial = self.getcompiled(snippet.factorial)
        assert factorial(5) == 120

    def test_simple_method(self):
        simple_method = self.getcompiled(snippet.simple_method)
        assert simple_method(55) == 55

    def test_sieve_of_eratosthenes(self):
        sieve_of_eratosthenes = self.getcompiled(snippet.sieve_of_eratosthenes)
        assert sieve_of_eratosthenes() == 1028

    def test_nested_whiles(self):
        nested_whiles = self.getcompiled(snippet.nested_whiles)
        assert nested_whiles(5,3) == '!!!!!'

    def test_call_five(self):
        call_five = self.getcompiled(snippet.call_five)
        result = call_five()
        assert result == [5]
        # --  currently result isn't a real list, but a pseudo-array
        #     that can't be inspected from Python.
        #self.assertEquals(result.__class__.__name__[:8], "list of ")

    def test_call_unpack_56(self):
        call_unpack_56 = self.getcompiled(snippet.call_unpack_56)
        result = call_unpack_56()
        assert result == (2, 5, 6)

    def test_class_defaultattr(self):
        class K:
            n = "hello"
        def class_defaultattr():
            k = K()
            k.n += " world"
            return k.n
        fn = self.getcompiled(class_defaultattr)
        assert fn() == "hello world"

    def test_tuple_repr(self):
        def tuple_repr(x=int, y=object):
            z = x, y
            while x:
                x = x-1
            return z
        fn = self.getcompiled(tuple_repr)
        assert fn(6,'a') == (6,'a')

    def test_classattribute(self):
        fn = self.getcompiled(snippet.classattribute)
        assert fn(1) == 123
        assert fn(2) == 456
        assert fn(3) == 789
        assert fn(4) == 789
        assert fn(5) == 101112

    def test_get_set_del_slice(self):
        fn = self.getcompiled(snippet.get_set_del_slice)
        l = list('abcdefghij')
        result = fn(l)
        assert l == [3, 'c', 8, 11, 'h', 9]
        assert result == ([3, 'c'], [9], [11, 'h'])

    def test_slice_long(self):
        def slice_long(l=list, n=long):
            return l[:n]
        fn = self.getcompiled(slice_long)
        l = list('abc')
        result = fn(l, 2**32)
        assert result == list('abc')
        result = fn(l, 2**64)
        assert result == list('abc')

    def test_type_conversion(self):
        # obfuscated test case specially for typer.insert_link_conversions()
        def type_conversion(n=int):
            if n > 3:
                while n > 0:
                    n = n-1
                    if n == 5:
                        n += 3.1416
            return n
        fn = self.getcompiled(type_conversion)
        assert fn(3) == 3
        assert fn(5) == 0
        assert abs(fn(7) + 0.8584) < 1E-5

    def test_do_try_raise_choose(self):
        fn = self.getcompiled(snippet.try_raise_choose)
        result = []
        for n in [-1,0,1,2]:
            result.append(fn(n))
        assert result == [-1,0,1,2]    

    def test_is_perfect_number(self):
        fn = self.getcompiled(snippet.is_perfect_number)
        for i in range(1, 33):
            perfect = fn(i)
            assert perfect is (i in (6,28))

    def test_prime(self):
        fn = self.getcompiled(snippet.prime)
        result = [fn(i) for i in range(1, 21)]
        assert result == [False, True, True, False, True, False, True, False,
                          False, False, True, False, True, False, False, False,
                          True, False, True, False]

    def test_mutate_global(self):
        class Stuff:
            pass
        g1 = Stuff(); g1.value = 1 
        g2 = Stuff(); g2.value = 2
        g3 = Stuff(); g3.value = 3
        g1.next = g3
        g2.next = g3
        g3.next = g3
        def do_things():
            g1.next = g1
            g2.next = g1
            g3.next = g2
            return g3.next.next.value
        fn = self.getcompiled(do_things)
        assert fn() == 1

    def test_float_ops(self):
        def f(x=float):
            return abs((-x) ** 3 + 1)
        fn = self.getcompiled(f)
        assert fn(-4.5) == 92.125
        assert fn(4.5) == 90.125

    def test_memoryerror(self):
        def f(i=int):
            lst = [0]*i
            lst[-1] = 5
            return lst[0]
        fn = self.getcompiled(f)
        assert fn(1) == 5
        assert fn(2) == 0
        py.test.raises(MemoryError, fn, sys.maxint//2+1)
        py.test.raises(MemoryError, fn, sys.maxint)

    def test_chr(self):
        def f(x=int):
            try:
                return 'Yes ' + chr(x)
            except ValueError:
                return 'No'
        fn = self.getcompiled(f)
        assert fn(65) == 'Yes A'
        assert fn(256) == 'No'
        assert fn(-1) == 'No'

    def test_unichr(self):
        def f(x=int):
            try:
                return ord(unichr(x))
            except ValueError:
                return -42
        fn = self.getcompiled(f)
        assert fn(65) == 65
        assert fn(-12) == -42
        assert fn(sys.maxint) == -42

    def test_list_indexerror(self):
        def f(i=int):
            lst = [123, 456]
            try:
                lst[i] = 789
            except IndexError:
                return 42
            return lst[0]
        fn = self.getcompiled(f)
        assert fn(1) == 123
        assert fn(2) == 42
        assert fn(-2) == 789
        assert fn(-3) == 42

    def test_long_long(self):
        from pypy.rpython.rarithmetic import r_ulonglong, r_longlong
        def f(i=r_ulonglong):
            return 4*i
        fn = self.getcompiled(f, view=False)
        assert fn(sys.maxint) == 4*sys.maxint

        def g(i=r_longlong):
            return 4*i
        gn = self.getcompiled(g, view=False)
        assert gn(sys.maxint) == 4*sys.maxint

    def test_specializing_int_functions(self):
        from pypy.rpython.rarithmetic import r_longlong
        def f(i):
            return i + 1
        f._annspecialcase_ = "specialize:argtype0"
        def g(n=int):
            if n > 0:
                return f(r_longlong(0))
            else:
                return f(0)

        fn = self.getcompiled(g)
        assert g(0) == 1
        assert g(1) == 1
