from cStringIO import StringIO
import py
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.backendopt.raisingop2direct_call import (
     raisingop2direct_call)
from pypy.translator.c.test import test_typed, test_lltyped
from pypy.translator.llvm import genllvm
from pypy.translator.translator import TranslationContext


class TestDatabase(object):
    def setup_method(self, meth):
        self.f = StringIO()
        genllvm.database = genllvm.Database(None, self.f)

    def test_repr_signed(self):
        assert genllvm.get_repr(rffi.r_long(-1)).TV == 'i64 -1'
        assert self.f.getvalue() == ''

    def test_repr_unsigned(self):
        assert genllvm.get_repr(rffi.r_ulong(1)).TV == 'i64 1'
        assert self.f.getvalue() == ''

    def test_repr_char(self):
        assert genllvm.get_repr(chr(123)).TV == 'i8 123'
        assert self.f.getvalue() == ''

    def test_repr_bool(self):
        assert genllvm.get_repr(True).TV == 'i1 true'
        assert genllvm.get_repr(False).TV == 'i1 false'
        assert self.f.getvalue() == ''

    def test_repr_float(self):
        assert genllvm.get_repr(0.3).TV == 'double 0.3'
        assert self.f.getvalue() == ''

    def test_repr_fixed_size_array(self):
        array = lltype.FixedSizeArray(lltype.Signed, 2)._container_example()
        assert genllvm.get_repr(array).TV == '[2 x i64] zeroinitializer'
        array.setitem(0, 1)
        array.setitem(1, 2)
        assert genllvm.get_repr(array).TV == ('[2 x i64] [\n'
                                              '    i64 1, i64 2\n'
                                              ']')
        assert self.f.getvalue() == ''

    def test_repr_string(self):
        array = lltype.FixedSizeArray(lltype.Char, 7)._container_example()
        for i, c in enumerate("string\00"):
            array.setitem(i, c)
        assert genllvm.get_repr(array).TV == r'[7 x i8] c"string\00"'
        assert self.f.getvalue() == ''

    def test_repr_struct(self):
        struct = lltype.Struct(
                'spam', ('eggs', lltype.Signed))._container_example()
        assert genllvm.get_repr(struct).TV == '%struct.spam zeroinitializer'
        struct.eggs = 1
        assert genllvm.get_repr(struct).TV == ('%struct.spam {\n'
                                                 '    i64 1 ; eggs\n'
                                                 '}')
        assert self.f.getvalue() == ('%struct.spam = type {\n'
                                     '    i64 ; eggs\n'
                                     '}\n')

    def test_repr_struct_nested(self):
        struct = lltype.Struct(
                'spam', ('eggs', lltype.Struct(
                        'foo', ('bar', lltype.Signed))))._container_example()
        assert genllvm.get_repr(struct).TV == '%struct.spam zeroinitializer'
        struct.eggs.bar = 1
        assert genllvm.get_repr(struct).TV == ('%struct.spam {\n'
                                                 '    %struct.foo {\n'
                                                 '        i64 1 ; bar\n'
                                                 '    } ; eggs\n'
                                                 '}')
        assert self.f.getvalue() == ('%struct.foo = type {\n'
                                     '    i64 ; bar\n'
                                     '}\n'
                                     '%struct.spam = type {\n'
                                     '    %struct.foo ; eggs\n'
                                     '}\n')

    def test_repr_array(self):
        array = lltype.Array(lltype.Signed)._container_example()
        assert genllvm.get_repr(array).TV == (
                '%array_of_i64_plus_1 {\n'
                '    i64 1, ; len\n'
                '    [1 x i64] zeroinitializer ; items\n'
                '}')
        array.setitem(0, 1)
        assert genllvm.get_repr(array).TV == (
                '%array_of_i64_plus_1 {\n'
                '    i64 1, ; len\n'
                '    [1 x i64] [\n'
                '        i64 1\n'
                '    ] ; items\n'
                '}')
        assert self.f.getvalue() == (
                '%array_of_i64_varsize = type {\n'
                '    i64, ; len\n'
                '    [0 x i64] ; items\n'
                '}\n'
                '%array_of_i64_plus_1 = type {\n'
                '    i64, ; len\n'
                '    [1 x i64] ; items\n'
                '}\n')

    def test_repr_array_of_ptr(self):
        struct_ptr_type = lltype.Ptr(lltype.Struct('x', ('y', lltype.Signed)))
        array = lltype.Array(struct_ptr_type)._container_example()
        assert genllvm.get_repr(array).TV == (
                '%array_of_struct.x_ptr_plus_1 {\n'
                '    i64 1, ; len\n'
                '    [1 x %struct.x*] zeroinitializer ; items\n'
                '}')
        array.setitem(0, struct_ptr_type._example())
        assert genllvm.get_repr(array).TV == (
                '%array_of_struct.x_ptr_plus_1 {\n'
                '    i64 1, ; len\n'
                '    [1 x %struct.x*] [\n'
                '        %struct.x* @global\n'
                '    ] ; items\n'
                '}')
        assert self.f.getvalue() == (
                '%struct.x = type {\n'
                '    i64 ; y\n'
                '}\n'
                '%array_of_struct.x_ptr_varsize = type {\n'
                '    i64, ; len\n'
                '    [0 x %struct.x*] ; items\n'
                '}\n'
                '%array_of_struct.x_ptr_plus_1 = type {\n'
                '    i64, ; len\n'
                '    [1 x %struct.x*] ; items\n'
                '}\n'
                '@global = global %struct.x zeroinitializer\n')

    def test_repr_func_type(self):
        func_type = lltype.FuncType([lltype.Signed], lltype.Void)
        assert genllvm.database.get_type(func_type).repr_type() == 'void (i64)'

    def test_repr_fixed_size_array_ptr(self):
        array_ptr = lltype.Ptr(
                lltype.FixedSizeArray(lltype.Signed, 2))._example()
        assert genllvm.get_repr(array_ptr).TV == '[2 x i64]* @global'
        assert self.f.getvalue() == (
                '@global = global [2 x i64] zeroinitializer\n')

    def test_repr_struct_ptr(self):
        struct_ptr = lltype.Ptr(
                lltype.Struct('spam', ('eggs', lltype.Signed)))._example()
        assert genllvm.get_repr(struct_ptr).TV == (
                '%struct.spam* @global')
        assert self.f.getvalue() == (
                '%struct.spam = type {\n'
                '    i64 ; eggs\n'
                '}\n'
                '@global = global %struct.spam zeroinitializer\n')

    def test_repr_array_ptr(self):
        array_ptr = lltype.Ptr(lltype.Array(lltype.Signed))._example()
        assert genllvm.get_repr(array_ptr).TV == (
                '%array_of_i64_varsize* bitcast(%array_of_i64_plus_1* '
                '@global to %array_of_i64_varsize*)')
        assert self.f.getvalue() == (
                '%array_of_i64_varsize = type {\n'
                '    i64, ; len\n'
                '    [0 x i64] ; items\n'
                '}\n'
                '%array_of_i64_plus_1 = type {\n'
                '    i64, ; len\n'
                '    [1 x i64] ; items\n'
                '}\n'
                '@global = global %array_of_i64_plus_1 {\n'
                '    i64 1, ; len\n'
                '    [1 x i64] zeroinitializer ; items\n'
                '}\n')

    def test_repr_nested_array_ptr(self):
        nested_array_ptr = lltype.Ptr(lltype.Struct(
                'foo', ('bar', lltype.Array(lltype.Signed))))._example()
        assert genllvm.get_repr(nested_array_ptr).TV == (
                '%struct.foo_varsize* bitcast(%struct.foo_plus_1* '
                '@global to %struct.foo_varsize*)')
        assert self.f.getvalue() == (
                '%array_of_i64_varsize = type {\n'
                '    i64, ; len\n'
                '    [0 x i64] ; items\n'
                '}\n'
                '%struct.foo_varsize = type {\n'
                '    %array_of_i64_varsize ; bar\n'
                '}\n'
                '%array_of_i64_plus_1 = type {\n'
                '    i64, ; len\n'
                '    [1 x i64] ; items\n'
                '}\n'
                '%struct.foo_plus_1 = type {\n'
                '    %array_of_i64_plus_1 ; bar\n'
                '}\n'
                '@global = global %struct.foo_plus_1 {\n'
                '    %array_of_i64_plus_1 {\n'
                '        i64 1, ; len\n'
                '        [1 x i64] zeroinitializer ; items\n'
                '    } ; bar\n'
                '}\n')


class _LLVMMixin(test_typed.CompilationTestCase):
    def annotatefunc(self, func, argtypes=None):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.backendopt.raisingop2direct_call = True
        config.translation.gc = 'none'
        config.translation.simplifying = True
        t = TranslationContext(config=config)
        if argtypes is None:
            argtypes = []
        a = t.buildannotator()
        a.build_types(func, argtypes)
        a.simplify()
        return t

    def compilefunc(self, t, func):
        gen_llvm = genllvm.GenLLVM(t, False)
        if hasattr(self, 'include_also_eci'):
            gen_llvm.ecis.append(self.include_also_eci)
        gen_llvm.gen_source(func)
        return gen_llvm.compile_module()

    def process(self, t):
        t.buildrtyper().specialize()
        raisingop2direct_call(t)


class TestLowLevelTypeLLVM(_LLVMMixin, test_lltyped.TestLowLevelType):
    def test_llgroup_size_limit(self):
        py.test.skip('takes too long to complete')

    def test_prebuilt_ll2ctypes_array(self):
        py.test.skip('not working yet')


class TestTypedLLVM(_LLVMMixin, test_typed.TestTypedTestCase):
    def test_memoryerror(self):
        py.test.skip('not working yet')

    def test_hash_preservation(self):
        py.test.skip('not working yet')

    def test_r_dict_exceptions(self):
        py.test.skip('not working yet')
