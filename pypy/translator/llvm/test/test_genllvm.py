from cStringIO import StringIO
import py
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.rlib.rarithmetic import LONG_BIT, r_uint, r_singlefloat
from pypy.rlib.test.test_longlong2float import enum_floats, fn, fnsingle
from pypy.rpython.lltypesystem import lltype, rffi, llmemory, llgroup
from pypy.rpython.lltypesystem.ll2ctypes import force_cast
from pypy.rpython.lltypesystem.test.test_rffi import BaseTestRffi
from pypy.rpython.test import (test_annlowlevel, test_exception,
     test_generator, test_rbool, test_rbuilder, test_rbuiltin, test_rclass,
     test_rconstantdict, test_rdict, test_remptydict, test_rfloat,
     test_rgeneric, test_rint, test_rlist, test_rpbc, test_rrange, test_rstr,
     test_rtuple, test_runicode, test_rvirtualizable2, test_rweakref)
from pypy.translator.backendopt.raisingop2direct_call import (
     raisingop2direct_call)
from pypy.translator.c.test import (test_typed, test_lltyped,
     test_backendoptimized, test_newgc, test_refcount)
from pypy.translator.llvm import genllvm
from pypy.translator.unsimplify import varoftype
from pypy.translator.translator import TranslationContext


class _Stub(object):
    def __getattr__(self, attr):
        return self
    def __call__(self, *args, **kwds):
        return None

LONG = 'i{}'.format(LONG_BIT)
def l(s):
    return s.replace('LONG', LONG)

class TestDatabase(object):
    def setup_method(self, meth):
        self.f = StringIO()
        genllvm.database = genllvm.Database(_Stub(), self.f)

    def test_repr_signed(self):
        assert genllvm.get_repr(-1).TV == l('LONG -1')
        assert self.f.getvalue() == ''

    def test_repr_unsigned(self):
        assert genllvm.get_repr(r_uint(1)).TV == l('LONG 1')
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
        assert genllvm.get_repr(array).TV == l('[2 x LONG] zeroinitializer')
        array.setitem(0, 1)
        array.setitem(1, 2)
        assert genllvm.get_repr(array).TV == l('[2 x LONG] [\n'
                                               '    LONG 1, LONG 2\n'
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
        assert genllvm.get_repr(struct).TV == '%spam zeroinitializer'
        struct.eggs = 1
        assert genllvm.get_repr(struct).TV == l('%spam {\n'
                                                '    LONG 1 ; eggs\n'
                                                '}')
        assert self.f.getvalue() == l('%spam = type {\n'
                                      '    LONG ; eggs\n'
                                      '}\n')

    def test_repr_struct_nested(self):
        struct = lltype.Struct(
                'spam', ('eggs', lltype.Struct(
                        'foo', ('bar', lltype.Signed))))._container_example()
        assert genllvm.get_repr(struct).TV == '%spam zeroinitializer'
        struct.eggs.bar = 1
        assert genllvm.get_repr(struct).TV == l('%spam {\n'
                                                '    %foo {\n'
                                                '        LONG 1 ; bar\n'
                                                '    } ; eggs\n'
                                                '}')
        assert self.f.getvalue() == l('%foo = type {\n'
                                      '    LONG ; bar\n'
                                      '}\n'
                                      '%spam = type {\n'
                                      '    %foo ; eggs\n'
                                      '}\n')

    def test_repr_array(self):
        array = lltype.Array(lltype.Signed)._container_example()
        assert genllvm.get_repr(array).TV == l(
                '%array_of_LONG_plus_1 {\n'
                '    LONG 1, ; len\n'
                '    [1 x LONG] zeroinitializer ; items\n'
                '}')
        array.setitem(0, 1)
        assert genllvm.get_repr(array).TV == l(
                '%array_of_LONG_plus_1 {\n'
                '    LONG 1, ; len\n'
                '    [1 x LONG] [\n'
                '        LONG 1\n'
                '    ] ; items\n'
                '}')
        assert self.f.getvalue() == l(
                '%array_of_LONG_varsize = type {\n'
                '    LONG, ; len\n'
                '    [0 x LONG] ; items\n'
                '}\n'
                '%array_of_LONG_plus_1 = type {\n'
                '    LONG, ; len\n'
                '    [1 x LONG] ; items\n'
                '}\n')

    def test_repr_array_of_ptr(self):
        struct_ptr_type = lltype.Ptr(lltype.Struct('x', ('y', lltype.Signed)))
        array = lltype.Array(struct_ptr_type)._container_example()
        assert genllvm.get_repr(array).TV == l(
                '%array_of_x_ptr_plus_1 {\n'
                '    LONG 1, ; len\n'
                '    [1 x %x*] zeroinitializer ; items\n'
                '}')
        array.setitem(0, struct_ptr_type._example())
        assert genllvm.get_repr(array).TV == l(
                '%array_of_x_ptr_plus_1 {\n'
                '    LONG 1, ; len\n'
                '    [1 x %x*] [\n'
                '        %x* @global\n'
                '    ] ; items\n'
                '}')
        assert self.f.getvalue() == l(
                '%x = type {\n'
                '    LONG ; y\n'
                '}\n'
                '%array_of_x_ptr_varsize = type {\n'
                '    LONG, ; len\n'
                '    [0 x %x*] ; items\n'
                '}\n'
                '%array_of_x_ptr_plus_1 = type {\n'
                '    LONG, ; len\n'
                '    [1 x %x*] ; items\n'
                '}\n'
                '@global = internal global %x zeroinitializer\n')

    def test_repr_func_type(self):
        func_type = lltype.FuncType([lltype.Signed], lltype.Void)
        assert genllvm.database.get_type(func_type).repr_type() == l(
                'void (LONG)')

    def test_repr_fixed_size_array_ptr(self):
        array_ptr = lltype.Ptr(
                lltype.FixedSizeArray(lltype.Signed, 2))._example()
        assert genllvm.get_repr(array_ptr).TV == l('[2 x LONG]* @global')
        assert self.f.getvalue() == l(
                '@global = internal global [2 x LONG] zeroinitializer\n')

    def test_repr_struct_ptr(self):
        struct_ptr = lltype.Ptr(
                lltype.Struct('spam', ('eggs', lltype.Signed)))._example()
        assert genllvm.get_repr(struct_ptr).TV == '%spam* @global'
        assert self.f.getvalue() == l(
                '%spam = type {\n'
                '    LONG ; eggs\n'
                '}\n'
                '@global = internal global %spam zeroinitializer\n')

    def test_repr_array_ptr(self):
        array_ptr = lltype.Ptr(lltype.Array(lltype.Signed))._example()
        assert genllvm.get_repr(array_ptr).TV == l(
                '%array_of_LONG_varsize* bitcast(%array_of_LONG_plus_1* '
                '@global to %array_of_LONG_varsize*)')
        assert self.f.getvalue() == l(
                '%array_of_LONG_varsize = type {\n'
                '    LONG, ; len\n'
                '    [0 x LONG] ; items\n'
                '}\n'
                '%array_of_LONG_plus_1 = type {\n'
                '    LONG, ; len\n'
                '    [1 x LONG] ; items\n'
                '}\n'
                '@global = internal global %array_of_LONG_plus_1 {\n'
                '    LONG 1, ; len\n'
                '    [1 x LONG] zeroinitializer ; items\n'
                '}\n')

    def test_repr_nested_array_ptr(self):
        nested_array_ptr = lltype.Ptr(lltype.Struct(
                'foo', ('bar', lltype.Array(lltype.Signed))))._example()
        assert genllvm.get_repr(nested_array_ptr).TV == (
                '%foo_varsize* bitcast(%foo_plus_1* @global to %foo_varsize*)')
        assert self.f.getvalue() == l(
                '%array_of_LONG_varsize = type {\n'
                '    LONG, ; len\n'
                '    [0 x LONG] ; items\n'
                '}\n'
                '%foo_varsize = type {\n'
                '    %array_of_LONG_varsize ; bar\n'
                '}\n'
                '%array_of_LONG_plus_1 = type {\n'
                '    LONG, ; len\n'
                '    [1 x LONG] ; items\n'
                '}\n'
                '%foo_plus_1 = type {\n'
                '    %array_of_LONG_plus_1 ; bar\n'
                '}\n'
                '@global = internal global %foo_plus_1 {\n'
                '    %array_of_LONG_plus_1 {\n'
                '        LONG 1, ; len\n'
                '        [1 x LONG] zeroinitializer ; items\n'
                '    } ; bar\n'
                '}\n')

    def test_typedef(self):
        TD = lltype.Typedef(lltype.Signed, 'test')
        assert genllvm.database.get_type(TD).repr_type() == l('LONG')

    def test_unique_name(self):
        assert genllvm.database.unique_name('@test') == '@test'
        assert genllvm.database.unique_name('@test') == '@test_1'
        assert genllvm.database.unique_name('@test_1') == '@test_1_1'
        assert genllvm.database.unique_name('%test') == '%test'
        assert genllvm.database.unique_name('%test') == '%test_1'
        assert genllvm.database.unique_name('@test:') == '@"test:"'
        assert genllvm.database.unique_name('@test:') == '@"test:_1"'


class _LLVMMixin(test_typed.CompilationTestCase):
    _func = None
    _types = None

    def __init__(self):
        self.config_override = {'translation.gc': 'ref'}
        self.annotator_policy = None

    def annotatefunc(self, func, argtypes=None):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.backendopt.raisingop2direct_call = True
        config.translation.simplifying = True
        config.override(self.config_override)
        t = self._translator = TranslationContext(config=config)
        if argtypes is None:
            argtypes = []
        a = t.buildannotator(self.annotator_policy)
        a.build_types(func, argtypes)
        a.simplify()
        return t

    def compilefunc(self, t, func):
        gen_llvm = self.genllvm = genllvm.GenLLVM(t, False)
        if hasattr(self, 'include_also_eci'):
            gen_llvm.ecis.append(self.include_also_eci)
            del self.include_also_eci
        gen_llvm.prepare(func, ())
        gen_llvm.gen_source()
        return gen_llvm.compile_module()

    def process(self, t):
        t.buildrtyper().specialize()
        raisingop2direct_call(t)

    def _compile(self, func, args, someobjects=False, policy=None):
        if someobjects:
            py.test.skip('PyObjects are not supported yet')
        types = [lltype.typeOf(arg) for arg in args]
        if not (func == self._func and types == self._types):
            self.config_override['translation.gcremovetypeptr'] = False
            self.annotator_policy = policy
            self._compiled = self.getcompiled(func, types)
            self._compiled.convert = False
            self._func = func
            self._types = types
        return self._compiled

    def interpret(self, func, args, **kwds):
        fc = self._compile(func, args, **kwds)
        return fc(*args)

    def interpret_raises(self, exception, func, args, **kwds):
        fc = self._compile(func, args, **kwds)
        with py.test.raises(exception):
            fc(*args)

    @property
    def translator(self):
        return self._translator


class TestSpecialCases(_LLVMMixin):
    def test_float_e_notation(self):
        def f():
            return 1e-06
        fc = self.getcompiled(f)
        assert fc() == 1e-06

    def test_two_exits_non_bool(self):
        genllvm.database = genllvm.Database(_Stub(), None)
        genllvm.database.genllvm.export = {}
        var = varoftype(lltype.Signed)
        startblock = Block([var])
        startblock.exitswitch = var
        startblock.closeblock(Link([var], Block([var])),
                              Link([var], Block([var])))
        startblock.exits[0].llexitcase = 0
        startblock.exits[1].llexitcase = 1
        graph = FunctionGraph('test', startblock, var)
        writer = genllvm.FunctionWriter()
        writer.write_graph('@test', graph)
        assert [line.strip() for line in writer.lines[-4:-1]] == [
                'badswitch:', 'call void @abort() noreturn nounwind',
                'unreachable']

    def test_empty_struct(self):
        T = lltype.Struct('empty', hints={'immutable': True})
        x1 = lltype.malloc(T, immortal=True)
        x2 = lltype.malloc(T, immortal=True)
        def f():
            return (lltype.cast_ptr_to_int(x1), lltype.cast_ptr_to_int(x2))
        fc = self.getcompiled(f)
        ret = fc()
        assert ret[0] != ret[1]

    def test_consider_constant_with_address(self):
        T = lltype.GcStruct('test')
        x = llmemory.cast_ptr_to_adr(lltype.malloc(T))
        def f():
            return len([x])
        fc = self.getcompiled(f)
        assert fc() == 1

    def test_consider_constant_with_llgroup(self):
        Y = lltype.GcStruct('Y')
        y = lltype.malloc(Y)
        X = lltype.Struct('X', ('y', lltype.Ptr(Y)))
        x = lltype.malloc(X, immortal=True)
        x.y = y
        grp = llgroup.group('test')
        offset = grp.add_member(x)
        grpptr = grp._as_ptr()
        def f():
            return len([(offset, grpptr)])
        fc = self.getcompiled(f)
        assert fc() == 1

    def test_consider_constant_with_llgroup_delayed(self):
        class X1(object):
            y = 11
        class X2(X1):
            y = 22
        class A1(object):
            x = X1()
        class A2(A1):
            x = X2()
        class B1(object):
            x = 1
        class B2(B1):
            x = 2
        def g(x):
            if x == 0:
                a = A1()
            else:
                a = A2()
            return a.x.y
        def f(x):
            if x == 0:
                b = B1()
            else:
                b = B2()
            # the expression `b.x` forces the type info group to be passed to
            # _consider_constant() before A1's vtable is added to the group
            return b.x * g(x)

        self.config_override['translation.gc'] = 'minimark'
        fc = self.getcompiled(f, [int])
        assert fc(0) == 11
        assert fc(1) == 44

    def test_int_abs(self):
        def f(x):
            return abs(x)
        fc = self.getcompiled(f, [int])
        assert fc(11) == 11
        assert fc(-22) == 22

    def test_new_erasing_pair(self):
        from pypy.rlib.rerased import new_erasing_pair
        erase, unerase = new_erasing_pair('test')

        class A(object):
            pass
        class B(object):
            pass

        a1 = A()
        a1.y = 11
        b1 = B()
        b1.x = erase(a1)
        a2 = A()
        a2.y = 22
        b2 = B()
        b2.x = erase(a2)

        def f(x):
            if x == 0:
                b = b1
            else:
                b = b2
            return unerase(b.x).y
        self.config_override['translation.gc'] = 'minimark'
        fc = self.getcompiled(f, [int])
        assert fc(0) == 11
        assert fc(1) == 22

    def test_void_arg(self):
        class A(object):
            def _freeze_(self):
                return True
        a = A()
        def g1(x):
            return 11
        def g2(x):
            return 22
        def f(x):
            g = [g1, g2][x]
            return g(a)
        fc = self.getcompiled(f, [int])
        assert fc(0) == 11
        assert fc(1) == 22

    def test_longlong2float(self):
        fn2 = self.getcompiled(fn, [float])
        for x in enum_floats():
            res = fn2(x)
            assert repr(res) == repr(x)

    def test_uint2singlefloat(self):
        fn2 = self.getcompiled(fnsingle, [float])
        for x in enum_floats():
            res = fn2(x)
            assert repr(res) == repr(float(r_singlefloat(x)))

    def test_float_neg(self):
        from math import copysign
        def f(x):
            return -x
        fc = self.getcompiled(f, [float])
        assert fc(1.0) == -1.0
        res = fc(0.0)
        assert res == -0.0
        assert copysign(1.0, res) == -1.0

    def test_llexternal_multiple_signatures(self):
        from pypy.module.fcntl import interp_fcntl
        def f(x):
            if x == 0:
                interp_fcntl.fcntl_int(0, 0, 0)
            elif x == 1:
                interp_fcntl.fcntl_str(0, 0, '')
        self.getcompiled(f, [int])

    def test_inet_ntoa(self):
        from pypy.rlib.rsocket import inet_ntoa
        def f(x):
            return inet_ntoa(x)
        self.getcompiled(f, [str])

    def test_cast_adr_to_int_symbolic(self):
        x = lltype.malloc(lltype.Struct(''), immortal=True)
        a = llmemory.cast_adr_to_int(llmemory.cast_ptr_to_adr(x), 'symbolic')
        b = llmemory.cast_adr_to_int(llmemory.NULL, 'symbolic')
        def f(x):
            if x == 0:
                return a
            else:
                return b
        fc = self.getcompiled(f, [int])
        assert fc(0) != 0
        assert fc(1) == 0

    def test_entrypoints(self):
        from pypy.rlib.entrypoint import entrypoint
        from pypy.translator.interactive import Translation

        def f():
            return 3

        key = 'test_entrypoints42'
        @entrypoint(key, [int], 'foobar')
        def g(x):
            return x + 42

        t = Translation(f, [], backend='llvm', secondaryentrypoints=key,
                        gcremovetypeptr=False)
        t.annotate()
        t.source_llvm()
        assert l('define LONG @foobar') in t.driver.llvmgen.base_path.new(
                ext='.ll').read()

    def test_export_struct(self):
        from pypy.rlib.exports import export_struct

        a = lltype.malloc(lltype.Struct('A'), immortal=True)
        export_struct('a', a._obj)

        def f():
            return len([a])
        self.getcompiled(f)
        assert '@a = global %A' in self.genllvm.base_path.new(ext='.ll').read()

    def test_export_struct_cast(self):
        from pypy.rlib.exports import export_struct
        use = rffi.llexternal('PYPY_NO_OP', [rffi.VOIDP], lltype.Void,
                              sandboxsafe=True, _nowrapper=True,
                              _callable=lambda: None)

        A = lltype.Struct('A', ('x', rffi.INT), ('y', rffi.INT))
        B = lltype.Struct('B', ('x', rffi.INT))
        buf = lltype.malloc(rffi.VOIDP.TO, 8, flavor='raw', zero=True)
        a = rffi.cast(lltype.Ptr(A), buf)
        b = rffi.cast(lltype.Ptr(B), buf)
        export_struct('a', a._obj)

        def f():
            use(rffi.cast(rffi.VOIDP, a))
            use(rffi.cast(rffi.VOIDP, b))
        self.getcompiled(f)
        assert '@a = global %A' in self.genllvm.base_path.new(ext='.ll').read()
        lltype.free(buf, 'raw')

    def test_ovf_op_in_loop(self):
        from sys import maxint
        from pypy.rlib.rarithmetic import ovfcheck
        def f(x, y):
            ret = 0
            for i in range(y):
                try:
                    ret = ovfcheck(x + i)
                except OverflowError:
                    break
            return ret
        fc = self.getcompiled(f, [int, int])
        assert fc(10, 10) == 19
        assert fc(maxint, 10) == maxint


class TestLowLevelTypeLLVM(_LLVMMixin, test_lltyped.TestLowLevelType):
    def test_union(self):
        py.test.skip('not supported')

    def test_llgroup_size_limit(self):
        py.test.skip('takes too long to complete')


class TestTypedLLVM(_LLVMMixin, test_typed.TestTypedTestCase):
    pass


class TestTypedOptimizedTestCaseLLVM(_LLVMMixin, test_backendoptimized
                                                 .TestTypedOptimizedTestCase):
    def process(self, t):
        test_backendoptimized.TestTypedOptimizedTestCase.process(self, t)

class TestTypedOptimizedSwitchTestCaseLLVM(test_backendoptimized
                                           .TestTypedOptimizedSwitchTestCase):
    class CodeGenerator(_LLVMMixin, test_backendoptimized
                                    .TestTypedOptimizedSwitchTestCase
                                    .CodeGenerator):
        def process(self, t):
            test_backendoptimized.TestTypedOptimizedSwitchTestCase \
                    .CodeGenerator.process(self, t)


class TestLLVMRffi(BaseTestRffi, _LLVMMixin):
    def compile(self, func, argtypes=None, backendopt=True, gcpolicy='ref'):
        # XXX do not ignore backendopt
        self.config_override['translation.gc'] = gcpolicy
        fn = self.getcompiled(func, argtypes)
        def fn2(*args, **kwds):
            kwds.pop('expected_extra_mallocs', None)
            return fn(*args, **kwds)
        return fn2


class TestMiniMarkGCLLVM(test_newgc.TestMiniMarkGC):
    @classmethod
    def _set_backend(cls, t):
        t.ensure_backend('llvm')

class TestMiniMarkGCMostCompactLLVM(test_newgc.TestMiniMarkGCMostCompact):
    @classmethod
    def _set_backend(cls, t):
        t.ensure_backend('llvm')


class TestRefcountLLVM(_LLVMMixin, test_refcount.TestRefcount):
    def compile_func(self, fn, inputtypes, t=None):
        if t is not None:
            py.test.skip('not supported yet')
        self.config_override['translation.gc'] = 'ref'
        return self.getcompiled(fn, inputtypes)


class TestRtypingLLVM(_LLVMMixin, test_annlowlevel.TestLLType):
    pass

class TestExceptionLLVM(_LLVMMixin, test_exception.TestLLtype):
    def test_raise_and_catch_other(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

    def test_raise_prebuilt_and_catch_other(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

class TestGeneratorLLVM(_LLVMMixin, test_generator.TestLLtype):
    pass

class TestRboolLLVM(_LLVMMixin, test_rbool.TestLLtype):
    pass

class TestStringBuilderLLVM(_LLVMMixin, test_rbuilder.TestLLtype):
    pass

class TestRbuiltinLLVM(_LLVMMixin, test_rbuiltin.TestLLtype):
    def test_debug_llinterpcall(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

class TestRclassLLVM(_LLVMMixin, test_rclass.TestLLtype):
    pass

class TestRconstantdictLLVM(_LLVMMixin, test_rconstantdict.TestLLtype):
    pass

class TestRdictLLVM(_LLVMMixin, test_rdict.TestLLtype):
    pass

class TestRemptydictLLVM(_LLVMMixin, test_remptydict.TestLLtype):
    pass

class TestRfloatLLVM(_LLVMMixin, test_rfloat.TestLLtype):
    pass

class TestRGenericLLVM(_LLVMMixin, test_rgeneric.TestLLRgeneric):
    pass

class TestRintLLVM(_LLVMMixin, test_rint.TestLLtype):
    pass

class TestRlistLLVM(_LLVMMixin, test_rlist.TestLLtype):
    def test_iterate_over_immutable_list(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

    def test_iterate_over_immutable_list_quasiimmut_attr(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

    def test_getitem_exc_1(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

    def test_getitem_exc_2(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

    def list_is_clear(self, lis, idx):
        items = lis._obj.items
        for i in range(idx, lis._obj.length):
            if items[i]._obj is not None:
                return False
        return True

class TestRPBCLLVM(_LLVMMixin, test_rpbc.TestLLtype):
    def read_attr(self, value, attr_name):
        class_name = 'pypy.rpython.test.test_rpbc.' + self.class_name(value)
        for (cd, _), ir in self._translator.rtyper.instance_reprs.items():
            if cd is not None and cd.name == class_name:
                value = force_cast(ir.lowleveltype, value)

        value = value._obj
        while value is not None:
            attr = getattr(value, "inst_" + attr_name, None)
            if attr is None:
                value = value.super
            else:
                return attr
        raise AttributeError()

class TestRPBCExtraLLVM(_LLVMMixin, test_rpbc.TestExtraLLtype):
    pass

class TestRrangeLLVM(_LLVMMixin, test_rrange.TestLLtype):
    pass

class TestRstrLLVM(_LLVMMixin, test_rstr.TestLLtype):
    def test_getitem_exc(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

class TestRtupleLLVM(_LLVMMixin, test_rtuple.TestLLtype):
    pass

class TestRUnicodeLLVM(_LLVMMixin, test_runicode.TestLLtype):
    def test_getitem_exc(self):
        py.test.skip('Impossible to pass if not running on LLInterpreter.')

class TestRvirtualizableLLVM(_LLVMMixin, test_rvirtualizable2.TestLLtype):
    pass

class TestRweakrefLLVM(_LLVMMixin, test_rweakref.TestLLtype):
    def _compile(self, *args, **kwds):
        self.config_override['translation.gc'] = 'minimark'
        return _LLVMMixin._compile(self, *args, **kwds)
