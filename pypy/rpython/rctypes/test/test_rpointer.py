"""
Test the rctypes pointer implementation
"""

import py
import pypy.rpython.rctypes.implementation
from pypy.translator.translator import TranslationContext
from pypy import conftest
from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy.annotation.model import SomeCTypesObject

from ctypes import c_int, c_double, POINTER, pointer, Structure

class Test_annotation:
    def test_simple(self):
        res = c_int(42)
        ptrres = POINTER(c_int)(res)
        assert res.value == ptrres.contents.value

    def test_annotate_c_int_ptr(self):
        ptrtype = POINTER(c_int)
        def func():
            res = c_int(42)
            ptrres  = ptrtype(res)
            return ptrres.contents.value
        
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        if conftest.option.view:
            t.view()

        assert s.knowntype == int

    def test_annotate_c_double(self):
        ptrtype = POINTER(c_double)
        def func():
            res = c_double(4.2)
            ptrres  = ptrtype(res)
            return ptrres.contents.value
        
        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        if conftest.option.view:
            t.view()

        assert s.knowntype == float

    def test_annotate_pointer_fn(self):
        def func():
            p = pointer(c_int(123))
            return p.contents.value

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(func, [])

        if conftest.option.view:
            t.view()

        assert s.knowntype == int

    def test_annotate_pointer_access_as_array(self):
        """
        Make sure that pointers work the same way as arrays.
        """
        def access_array():
            # Never run this function!
            my_pointer = pointer(c_int(10))
            my_pointer[0] = c_int(1)
            my_pointer[1] = 2    # <== because of this

            return my_pointer[0]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_array, [])
        assert s.knowntype == int

        if conftest.option.view:
            t.view()

    def test_annotate_prebuilt(self):
        c = c_int(10)
        p = pointer(c)
        def access_prebuilt():
            p.contents.value += 1
            return p[0]

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(access_prebuilt, [])
        assert s.knowntype == int

        if conftest.option.view:
            t.view()

    def test_annotate_ass_contents(self):
        def fn():
            x = c_int(5)
            y = c_int(6)
            p = pointer(x)
            p.contents = y
            y.value = 12
            return p.contents.value

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(fn, [])
        assert s.knowntype == int

        if conftest.option.view:
            t.view()

    def test_annotate_POINTER(self):
        def fn():
            p = POINTER(c_double)()
            p.contents = c_double(6.1)
            return p

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(fn, [])
        assert s.knowntype == POINTER(c_double)

        if conftest.option.view:
            t.view()

    def test_annotate_mixed_ownership(self):
        def fn(n):
            if n > 0:
                p = pointer(c_int())
                q = p.contents
            else:
                q = c_int()
            return q

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(fn, [int])
        assert isinstance(s, SomeCTypesObject)
        assert not s.ownsmemory


class Test_specialization:
    def test_specialize_c_int_ptr(self):
        ptrtype = POINTER(c_int)
        def func():
            res = c_int(42)
            ptrres = ptrtype(res)
            return ptrres.contents.value

        res = interpret(func, [])
        assert res == 42

    def test_specialize_mutate_via_pointer(self):
        ptrtype = POINTER(c_int)
        def func():
            res = c_int(6)
            p1 = ptrtype(res)
            p2 = ptrtype(p1.contents)
            p2.contents.value *= 7
            return res.value

        res = interpret(func, [])
        assert res == 42

    def test_keepalive(self):
        ptrtype = POINTER(c_int)
        def func(n):
            if n == 1:
                x = c_int(6)
                p1 = ptrtype(x)
            else:
                y = c_int(7)
                p1 = ptrtype(y)
            # x or y risk being deallocated by the time we get there,
            # unless p1 correctly keeps them alive.  The llinterpreter
            # detects this error exactly.
            return p1.contents.value

        res = interpret(func, [3])
        assert res == 7

    def test_keepalive_2(self):
        ptrtype = POINTER(c_int)
        ptrptrtype = POINTER(ptrtype)
        def func(n):
            if n == 1:
                p1 = ptrtype(c_int(6))
                p2 = ptrptrtype(p1)
            else:
                if n == 2:
                    p1 = ptrtype(c_int(7))
                else:
                    p1 = ptrtype(c_int(8))
                p2 = ptrptrtype(p1)
            del p1
            p3 = ptrptrtype(p2.contents)
            p3.contents.contents.value *= 6
            return p2.contents.contents.value

        assert func(2) == 42
        res = interpret(func, [2])
        assert res == 42

    def test_specialize_pointer_fn(self):
        def func():
            p = pointer(c_int(123))
            return p.contents.value

        assert func() == 123
        res = interpret(func, [])
        assert res == 123

    def test_specialize_pointer_access_as_array(self):
        """
        Make sure that pointers work the same way as arrays.
        """
        def access_array():
            my_int = c_int(11)
            my_pointer = pointer(my_int)
            x = my_pointer[0]
            my_pointer[0] = c_int(7)
            assert my_int.value == 7
            y = my_pointer[0]
            my_pointer[0] = 5
            assert my_int.value == 5
            z = my_pointer.contents.value
            return x * y * z

        assert access_array() == 5 * 7 * 11
        res = interpret(access_array, [])
        assert res == 5 * 7 * 11

    def test_specialize_prebuilt(self):
        c = c_int(10)
        p = pointer(c)
        def access_prebuilt():
            p.contents.value += 1
            return p[0]

        res = interpret(access_prebuilt, [])
        assert res == 11

    def test_specialize_ass_contents(self):
        def fn():
            x = c_int(5)
            y = c_int(6)
            p = pointer(x)
            p.contents = y
            y.value = 12
            return p.contents.value

        res = interpret(fn, [])
        assert res == 12

    def test_specialize_POINTER(self):
        def fn():
            p = POINTER(c_double)()
            p.contents = c_double(6.25)
            return p

        res = interpret(fn, [])
        float_c_data = res.c_data[0]
        assert float_c_data[0] == 6.25

    def test_specialize_getitem_nonzero_index(self):
        A = c_int * 10
        class S(Structure):
            _fields_ = [('x', POINTER(c_int))]
        def fn():
            a = A()
            a[3] = 5
            s = S()
            s.x = a
            return s.x[3]
        assert fn() == 5
        res = interpret(fn, [])
        assert res == 5

    def test_specialize_null_pointer(self):
        def fn():
            p = POINTER(c_int)()
            assert not p
            p.contents = c_int(12)
            assert p
        interpret(fn, [])

    def test_specialize_mixed_ownership(self):
        def fn(n):
            a = c_int(55)
            if n > 0:
                p = pointer(a)
                q = p.contents
            else:
                q = c_int()
            q.value = n
            return a.value
        res = interpret(fn, [12])
        assert res == 12
        res = interpret(fn, [-12])
        assert res == 55

class Test_compilation:
    def test_compile_getitem_nonzero_index(self):
        A = c_int * 10
        class S(Structure):
            _fields_ = [('x', POINTER(c_int))]
        def func():
            a = A()
            a[3] = 5
            s = S()
            s.x = a
            return s.x[3]
        fn = compile(func, [])
        res = fn()
        assert res == 5
