import autopath
from pypy.translator.tool.buildpyxmodule import skip_missing_compiler
from pypy.translator.translator import Translator

from pypy.translator.test import snippet 

# XXX this tries to make compiling faster for full-scale testing
from pypy.translator.tool import buildpyxmodule
buildpyxmodule.enable_fast_compilation()

class TestAnnotatedTestCase:

    def getcompiled(self, func):
        t = Translator(func, simplifying=True)
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        a = t.annotate(argstypelist)
        a.simplify()
        return skip_missing_compiler(t.ccompile)

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
