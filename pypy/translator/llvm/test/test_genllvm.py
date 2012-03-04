from cStringIO import StringIO
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.interactive import Translation
from pypy.translator.llvm import genllvm


def compile(func, argtypes=None, gc=False):
    translation = Translation(func, argtypes, backend='llvm', verbose=False)
    translation.disable(['backendopt_lltype'])
    translation.config.translation.backendopt.none = True
    if gc:
        translation.config.translation.gctransformer = 'framework'
        translation.config.translation.gc = 'minimark'
    else:
        translation.config.translation.gctransformer = 'none'
        translation.config.translation.gc = 'none'

    translation.annotate()
    return translation.compile_llvm()


class TestPrimitives(object):
    def setup(self):
        genllvm.database = None

    def test_repr_signed(self):
        assert genllvm.TV(genllvm.C(rffi.r_long(-1))) == 'i64 -1'

    def test_repr_unsigned(self):
        assert genllvm.TV(genllvm.C(rffi.r_ulong(1))) == 'i64 1'

    def test_repr_char(self):
        assert genllvm.TV(genllvm.C(chr(123))) == 'i8 123'

    def test_repr_bool(self):
        assert genllvm.TV(genllvm.C(True)) == 'i1 true'
        assert genllvm.TV(genllvm.C(False)) == 'i1 false'

    def test_repr_float(self):
        assert genllvm.TV(genllvm.C(0.3)) == 'double 0.3'


class TestDatabase(object):
    def setup_method(self, meth):
        self.f = StringIO()
        genllvm.database = genllvm.Database(None, self.f)

    def test_repr_fixed_size_array(self):
        array = lltype.FixedSizeArray(lltype.Signed, 2)._container_example()
        assert genllvm.TV(genllvm.C(array)) == '[2 x i64] zeroinitializer'
        array.setitem(0, 1)
        array.setitem(1, 2)
        assert genllvm.TV(genllvm.C(array)) == ('[2 x i64] [\n'
                                                '    i64 1, i64 2\n'
                                                ']')
        assert self.f.getvalue() == ''

    def test_repr_string(self):
        array = lltype.FixedSizeArray(lltype.Char, 7)._container_example()
        for i, c in enumerate("string\00"):
            array.setitem(i, c)
        assert genllvm.TV(genllvm.C(array)) == r'[7 x i8] c"string\00"'
        assert self.f.getvalue() == ''

    def test_repr_struct(self):
        struct = lltype.Struct(
                'spam', ('eggs', lltype.Signed))._container_example()
        assert genllvm.TV(genllvm.C(struct)) == '%struct.spam zeroinitializer'
        struct.eggs = 1
        assert genllvm.TV(genllvm.C(struct)) == ('%struct.spam {\n'
                                                 '    i64 1 ; eggs\n'
                                                 '}')
        assert self.f.getvalue() == ('%struct.spam = type {\n'
                                     '    i64 ; eggs\n'
                                     '}\n')

    def test_repr_struct_nested(self):
        struct = lltype.Struct(
                'spam', ('eggs', lltype.Struct(
                        'foo', ('bar', lltype.Signed))))._container_example()
        assert genllvm.TV(genllvm.C(struct)) == '%struct.spam zeroinitializer'
        struct.eggs.bar = 1
        assert genllvm.TV(genllvm.C(struct)) == ('%struct.spam {\n'
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
        assert genllvm.TV(genllvm.C(array)) == (
                '%array_of_i64 { i64 1, [1 x i64] zeroinitializer }')
        array.setitem(0, 1)
        assert genllvm.TV(genllvm.C(array)) == (
                '%array_of_i64 { i64 1, [1 x i64] [\n'
                '    i64 1\n'
                '] }')
        assert self.f.getvalue() == '%array_of_i64 = type { i64, [0 x i64] }\n'

    def test_repr_array_of_ptr(self):
        struct_ptr_type = lltype.Ptr(lltype.Struct('x', ('y', lltype.Signed)))
        array = lltype.Array(struct_ptr_type)._container_example()
        assert genllvm.TV(genllvm.C(array)) == (
                '%array_of_struct.x_ptr '
                '{ i64 1, [1 x %struct.x*] zeroinitializer }')
        array.setitem(0, struct_ptr_type._example())
        assert genllvm.TV(genllvm.C(array)) == (
                '%array_of_struct.x_ptr { i64 1, [1 x %struct.x*] [\n'
                '    %struct.x* @global_struct.x\n'
                '] }')
        assert self.f.getvalue() == (
                '%struct.x = type {\n'
                '    i64 ; y\n'
                '}\n'
                '%array_of_struct.x_ptr = type { i64, [0 x %struct.x*] }\n'
                '@global_struct.x = global %struct.x zeroinitializer\n')

    def test_repr_func_type(self):
        func_type = lltype.FuncType([lltype.Signed], lltype.Void)
        assert genllvm._T(func_type) == 'void (i64)'

    def test_repr_fixed_size_array_ptr(self):
        array_ptr = lltype.Ptr(
                lltype.FixedSizeArray(lltype.Signed, 2))._example()
        assert genllvm.TV(genllvm.C(array_ptr)) == '[2 x i64]* @global_array'
        assert self.f.getvalue() == (
                '@global_array = global [2 x i64] zeroinitializer\n')

    def test_repr_struct_ptr(self):
        struct_ptr = lltype.Ptr(
                lltype.Struct('spam', ('eggs', lltype.Signed)))._example()
        assert genllvm.TV(genllvm.C(struct_ptr)) == (
                '%struct.spam* @global_struct.spam')
        assert self.f.getvalue() == (
                '%struct.spam = type {\n'
                '    i64 ; eggs\n'
                '}\n'
                '@global_struct.spam = global %struct.spam zeroinitializer\n')

    def test_repr_array_ptr(self):
        array_ptr = lltype.Ptr(lltype.Array(lltype.Signed))._example()
        assert genllvm.TV(genllvm.C(array_ptr)) == (
                '%array_of_i64* bitcast({ i64, [1 x i64] }* '
                '@global_array_of_i64 to %array_of_i64*)')
        assert self.f.getvalue() == (
                '%array_of_i64 = type { i64, [0 x i64] }\n'
                '@global_array_of_i64 = global { i64, [1 x i64] } '
                '{ i64 1, [1 x i64] zeroinitializer }\n')


class TestSimple(object):
    def test_pass(self):
        def f():
            pass

        fc = compile(f)
        assert fc() == 0

    def test_return(self):
        def f():
            return 42

        fc = compile(f)
        assert fc() == 42

    def test_argument(self):
        def f(echo):
            return echo

        fc = compile(f, [int])
        assert fc(123) == 123

    def test_add_int(self):
        def f(i):
            return i + 1

        fc = compile(f, [int])
        assert fc(2) == 3
        assert fc(3) == 4

    def test_call(self):
        def g():
            return 11
        def f():
            return g()

        fc = compile(f)
        assert fc() == 11

    def test_bool(self):
        def f(b):
            return not b

        fc = compile(f, [bool])
        assert fc(True) == False
        assert fc(False) == True


class TestGarbageCollected(object):
    def test_struct(self):
        class C(object):
            pass

        def f(i):
            c = C()
            c.i = i
            return c.i

        fc = compile(f, [int], gc=True)
        assert fc(33) == 33
