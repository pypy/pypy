"""
Test the c_void_p implementation.
"""

import py.test
import pypy.rpython.rctypes.implementation
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.annotation import model as annmodel
from pypy.translator.translator import TranslationContext
from pypy.translator.c.test.test_genc import compile
from pypy import conftest
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.test.test_llinterp import interpret

from ctypes import c_void_p, c_int, c_long, cast, pointer, POINTER
from ctypes import c_char, c_byte, c_char_p, create_string_buffer, CFUNCTYPE

class Test_annotation:
    def test_annotate_c_void_p(self):
        def fn():
            x = c_int(12)
            p1 = cast(pointer(x), c_void_p)
            p2 = cast(p1, POINTER(c_int))
            assert p2.contents.value == 12
            return p1, p2

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(fn, [])
        assert s.items[0].knowntype == c_void_p
        assert s.items[1].knowntype == POINTER(c_int)

        if conftest.option.view:
            t.view()

    def test_annotate_addr2int(self):
        def fn():
            x = c_int(12)
            p1 = cast(pointer(x), c_void_p)
            return p1.value

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(fn, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_annotate_int2addr(self):
        def fn():
            return c_void_p(123)

        t = TranslationContext()
        a = t.buildannotator()
        s = a.build_types(fn, [])
        assert s.knowntype == c_void_p

class Test_specialization:
    def test_specialize_c_void_p(self):
        def func():
            x = c_int(12)
            p1 = cast(pointer(x), c_void_p)
            p2 = cast(p1, POINTER(c_int))
            return p1, p2.contents.value

        res = interpret(func, [])
        assert lltype.typeOf(res.item0.c_data[0]) == llmemory.Address
        assert res.item1 == 12

    def test_truth_value(self):
        def func():
            assert not c_void_p()
        interpret(func, [])

    def test_None_argument(self):
        def func():
            return bool(c_void_p(None))
        res = interpret(func, [])
        assert res is False

    def test_convert_pointers(self):
        strlen = CFUNCTYPE(c_int, c_void_p)()
        strlen.__name__ = 'strlen'
        def ll_strlen_from_void_p(adr):
            i = 0
            while adr.char[i] != '\x00':
                i += 1
            return i
        strlen.llinterp_friendly_version = ll_strlen_from_void_p
        PTR = c_char_p("hello")
        BUF = create_string_buffer(10)
        BUF.value = "hello"
        ARR = (c_byte * 10)(65, 66, 67)

        def func(n):
            # constant arguments XXX in-progress
            ##   assert strlen("hello") == 5
            ##   assert strlen(PTR) == 5
            ##   assert strlen(BUF) == 5
            ##   assert strlen(ARR) == 3
            # variable arguments
            s = chr(n) + 'bc'
            assert strlen(s) == 3
            assert strlen(c_char_p(s)) == 3
            assert strlen((c_char * 6)('a', 'b')) == 2
            # XXX Bytes are not chars in llinterp.
            # assert strlen((c_byte * 6)(104,101,108,108,111)) == 5
            buf = create_string_buffer(10)
            buf.value = "hello"
            assert strlen(buf) == 5

        interpret(func, [65])

    def test_specialize_addr2int(self):
        def fn():
            x = c_int(12)
            p1 = cast(pointer(x), c_void_p)
            return p1.value
        res = interpret(fn, [])
        assert lltype.typeOf(res) == lltype.Signed    # xxx

class Test_compilation:
    def test_compile_c_char_p(self):
        def func():
            x = c_int(12)
            p1 = cast(pointer(x), c_void_p)
            p2 = cast(p1, POINTER(c_int))
            return p2.contents.value

        fn = compile(func, [])
        assert fn() == 12

    def test_compile_funcptr_as_void_p(self):
        from pypy.rpython.rctypes.test.test_rfunc import labs
        UNARYFN = CFUNCTYPE(c_long, c_long)
        def func(n):
            if n < -100:
                p1 = c_void_p()   # NULL void pointer - don't try!
            else:
                p1 = cast(labs, c_void_p)
            p2 = cast(p1, UNARYFN)
            return p2(n)

        assert func(-41) == 41
        assert func(72) == 72

        fn = compile(func, [int])
        assert fn(-42) == 42
        assert fn(71) == 71

    def test_compile_int2addr(self):
        def func(n):
            return c_void_p(n).value
        fn = compile(func, [int])
        assert fn(123) == 123
