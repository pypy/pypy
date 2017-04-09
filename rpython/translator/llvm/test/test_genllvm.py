import __builtin__
from cStringIO import StringIO
import ctypes
import py
from pypy.config.pypyoption import get_pypy_config
from rpython.flowspace.model import FunctionGraph, Block, Link
from rpython.rlib.rarithmetic import (LONG_BIT, r_uint, r_singlefloat,
     r_longfloat)
from rpython.rlib.test.test_longlong2float import enum_floats, fn, fnsingle
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.rtyper.lltypesystem.ll2ctypes import (get_ctypes_type,
     lltype2ctypes, ctypes2lltype)
from rpython.rtyper.rtuple import TupleRepr
from rpython.rtyper.lltypesystem.lltype import getfunctionptr
from rpython.rtyper.lltypesystem.rstr import StringRepr, UnicodeRepr
from rpython.rtyper.lltypesystem.test.test_rffi import BaseTestRffi
from rpython.rtyper.test.tool import BaseRtypingTest
from rpython.translator.backendopt.all import backend_optimizations
from rpython.translator.c.test import (test_typed, test_lltyped,
     test_backendoptimized, test_newgc, test_refcount)
from rpython.translator.llvm import genllvm as genllvm_mod
from rpython.translator.unsimplify import varoftype
from rpython.translator.transform import insert_ll_stackcheck
from rpython.translator.translator import TranslationContext


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
        genllvm_mod.database = genllvm_mod.Database(_Stub(), self.f)

    def test_repr_signed(self):
        assert genllvm_mod.get_repr(-1).TV == l('LONG -1')
        assert self.f.getvalue() == ''

    def test_repr_unsigned(self):
        assert genllvm_mod.get_repr(r_uint(1)).TV == l('LONG 1')
        assert self.f.getvalue() == ''

    def test_repr_char(self):
        assert genllvm_mod.get_repr(chr(123)).TV == 'i8 123'
        assert self.f.getvalue() == ''

    def test_repr_bool(self):
        assert genllvm_mod.get_repr(True).TV == 'i1 true'
        assert genllvm_mod.get_repr(False).TV == 'i1 false'
        assert self.f.getvalue() == ''

    def test_repr_float(self):
        assert genllvm_mod.get_repr(0.3).TV == 'double 0.3'
        assert self.f.getvalue() == ''

    def test_repr_fixed_size_array(self):
        array = lltype.FixedSizeArray(lltype.Signed, 2)._container_example()
        assert genllvm_mod.get_repr(array).TV == l(
                '[2 x LONG] zeroinitializer')
        array.setitem(0, 1)
        array.setitem(1, 2)
        assert genllvm_mod.get_repr(array).TV == l('[2 x LONG] [\n'
                                                   '    LONG 1, LONG 2\n'
                                                   ']')
        assert self.f.getvalue() == ''

    def test_repr_string(self):
        array = lltype.FixedSizeArray(lltype.Char, 7)._container_example()
        for i, c in enumerate("string\00"):
            array.setitem(i, c)
        assert genllvm_mod.get_repr(array).TV == r'[7 x i8] c"string\00"'
        assert self.f.getvalue() == ''

    def test_repr_struct(self):
        struct = lltype.Struct(
                'spam', ('eggs', lltype.Signed))._container_example()
        assert genllvm_mod.get_repr(struct).TV == '%spam zeroinitializer'
        struct.eggs = 1
        assert genllvm_mod.get_repr(struct).TV == l('%spam {\n'
                                                    '    LONG 1 ; eggs\n'
                                                    '}')
        assert self.f.getvalue() == l('%spam = type {\n'
                                      '    LONG ; eggs\n'
                                      '}\n')

    def test_repr_struct_nested(self):
        struct = lltype.Struct(
                'spam', ('eggs', lltype.Struct(
                        'foo', ('bar', lltype.Signed))))._container_example()
        assert genllvm_mod.get_repr(struct).TV == '%spam zeroinitializer'
        struct.eggs.bar = 1
        assert genllvm_mod.get_repr(struct).TV == l('%spam {\n'
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
        assert genllvm_mod.get_repr(array).TV == l(
                '%array_of_LONG_plus_1 {\n'
                '    LONG 1, ; len\n'
                '    [1 x LONG] zeroinitializer ; items\n'
                '}')
        array.setitem(0, 1)
        assert genllvm_mod.get_repr(array).TV == l(
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
        assert genllvm_mod.get_repr(array).TV == l(
                '%array_of_x_ptr_plus_1 {\n'
                '    LONG 1, ; len\n'
                '    [1 x %x*] zeroinitializer ; items\n'
                '}')
        array.setitem(0, struct_ptr_type._example())
        assert genllvm_mod.get_repr(array).TV == l(
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
        assert genllvm_mod.database.get_type(func_type).repr_type() == l(
                'void (LONG)')

    def test_repr_fixed_size_array_ptr(self):
        array_ptr = lltype.Ptr(
                lltype.FixedSizeArray(lltype.Signed, 2))._example()
        assert genllvm_mod.get_repr(array_ptr).TV == l('[2 x LONG]* @global')
        assert self.f.getvalue() == l(
                '@global = internal global [2 x LONG] zeroinitializer\n')

    def test_repr_struct_ptr(self):
        struct_ptr = lltype.Ptr(
                lltype.Struct('spam', ('eggs', lltype.Signed)))._example()
        assert genllvm_mod.get_repr(struct_ptr).TV == '%spam* @global'
        assert self.f.getvalue() == l(
                '%spam = type {\n'
                '    LONG ; eggs\n'
                '}\n'
                '@global = internal global %spam zeroinitializer\n')

    def test_repr_array_ptr(self):
        array_ptr = lltype.Ptr(lltype.Array(lltype.Signed))._example()
        assert genllvm_mod.get_repr(array_ptr).TV == l(
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
        assert genllvm_mod.get_repr(nested_array_ptr).TV == (
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
        assert genllvm_mod.database.get_type(TD).repr_type() == l('LONG')

    def test_unique_name(self):
        assert genllvm_mod.database.unique_name('@test') == '@test'
        assert genllvm_mod.database.unique_name('@test') == '@test_1'
        assert genllvm_mod.database.unique_name('@test_1') == '@test_1_1'
        assert genllvm_mod.database.unique_name('%test') == '%test'
        assert genllvm_mod.database.unique_name('%test') == '%test_1'
        assert genllvm_mod.database.unique_name('@test:') == '@"test:"'
        assert genllvm_mod.database.unique_name('@test:') == '@"test:_1"'


class CTypesFuncWrapper(object):
    def __init__(self, genllvm, graph, path):
        self.graph = graph
        self.rtyper = genllvm.translator.rtyper
        self.convert = True
        cdll = ctypes.CDLL(path)
        setup_ptr = genllvm.gcpolicy.get_setup_ptr()
        if setup_ptr is not None:
            self.setup_func = self._func(cdll, setup_ptr)
        else:
            self.setup_func = None
        self.entry_point = self._func(
                cdll, getfunctionptr(self.graph))
        self.rpyexc_clear = self._func(
                cdll, genllvm.exctransformer.rpyexc_clear_ptr.value)
        self.rpyexc_occured = self._func(
                cdll, genllvm.exctransformer.rpyexc_occured_ptr.value)
        self.rpyexc_fetch_type = self._func(
                cdll, genllvm.exctransformer.rpyexc_fetch_type_ptr.value)

    def _func(self, cdll, func_ptr):
        func = getattr(cdll, genllvm_mod.get_repr(func_ptr).V[1:])
        func.restype = get_ctypes_type(func_ptr._T.RESULT)
        func.argtypes = map(get_ctypes_type, func_ptr._T.ARGS)
        def _call(*args):
            ret = func(*(lltype2ctypes(arg) for arg in args))
            return ctypes2lltype(func_ptr._T.RESULT, ret)
        return _call

    def __call__(self, *args, **kwds):
        expected_exception_name = kwds.pop('expected_exception_name', None)
        if self.convert:
            getrepr = self.rtyper.bindingrepr
            args = [self._Repr2lltype(getrepr(var), arg)
                    for var, arg in zip(self.graph.getargs(), args)]
        if self.setup_func:
            self.setup_func()
        self.rpyexc_clear()
        ret = self.entry_point(*args)
        if self.rpyexc_occured():
            name = ''.join(self.rpyexc_fetch_type().name.chars)
            if expected_exception_name is not None:
                assert name == expected_exception_name
                return
            if name == 'UnicodeEncodeError':
                raise UnicodeEncodeError('', u'', 0, 0, '')
            raise getattr(__builtin__, name, RuntimeError)
        if self.convert:
            return self._lltype2Repr(getrepr(self.graph.getreturnvar()), ret)
        return ret

    def _Repr2lltype(self, repr_, value):
        if isinstance(repr_.lowleveltype, lltype.Primitive):
            return value
        return {StringRepr: BaseRtypingTest.string_to_ll,
                UnicodeRepr: BaseRtypingTest.unicode_to_ll
               }[repr_.__class__](value)

    def _lltype2Repr(self, repr_, value):
        if isinstance(repr_.lowleveltype, lltype.Primitive):
            return value
        return {TupleRepr: lambda value: tuple(
                    self._lltype2Repr(item_r, getattr(value, name))
                    for item_r, name in zip(repr_.items_r, repr_.fieldnames)),
                StringRepr: BaseRtypingTest.ll_to_string,
                UnicodeRepr: BaseRtypingTest.ll_to_unicode
               }[repr_.__class__](value)


class _LLVMMixin(object):
    _func = None
    _types = None

    def getcompiled(self, func, argtypes, gcpolicy='ref', backendopt=True,
                    annotator_policy=None, no_gcremovetypeptr=False):
        config = get_pypy_config(translating=True)
        config.translation.gc = gcpolicy
        if no_gcremovetypeptr:
            config.translation.gcremovetypeptr = False
        t = self._translator = TranslationContext(config=config)
        a = t.buildannotator(annotator_policy)
        a.build_types(func, argtypes)
        a.simplify()
        t.buildrtyper().specialize()
        if py.test.config.option.view:
            t.view()
        if backendopt:
            backend_optimizations(self.translator)

        t.checkgraphs()
        insert_ll_stackcheck(t)

        genllvm = self.genllvm = genllvm_mod.GenLLVM(t)
        graph = a.bookkeeper.getdesc(func).getuniquegraph()
        setup = genllvm.gcpolicy.get_setup_ptr()
        genllvm.prepare(None, ([setup] if setup is not None else []) + [
                getfunctionptr(graph),
                genllvm.exctransformer.rpyexc_clear_ptr.value,
                genllvm.exctransformer.rpyexc_occured_ptr.value,
                genllvm.exctransformer.rpyexc_fetch_type_ptr.value])
        genllvm.gen_source()
        so_file = genllvm._compile(True)
        return CTypesFuncWrapper(genllvm, graph, str(so_file))

    @property
    def translator(self):
        return self._translator


class TestSpecialCases(_LLVMMixin):
    def test_float_e_notation(self):
        def f():
            return 1e-06
        fc = self.getcompiled(f, [])
        assert fc() == 1e-06

    def test_two_exits_non_bool(self):
        genllvm_mod.database = genllvm_mod.Database(_Stub(), None)
        genllvm_mod.database.target_attributes = ''
        genllvm_mod.database.genllvm.entrypoints = set()
        var = varoftype(lltype.Signed)
        startblock = Block([var])
        startblock.exitswitch = var
        startblock.closeblock(Link([var], Block([var])),
                              Link([var], Block([var])))
        startblock.exits[0].llexitcase = 0
        startblock.exits[1].llexitcase = 1
        graph = FunctionGraph('test', startblock, var)
        writer = genllvm_mod.FunctionWriter()
        writer.write_graph(None, '@test', graph, False)
        assert [line.strip() for line in writer.lines[-4:-1]] == [
                'badswitch:', 'call void @abort() noreturn nounwind',
                'unreachable']

    def test_empty_struct(self):
        T = lltype.Struct('empty', hints={'immutable': True})
        x1 = lltype.malloc(T, immortal=True)
        x2 = lltype.malloc(T, immortal=True)
        def f():
            return (lltype.cast_ptr_to_int(x1), lltype.cast_ptr_to_int(x2))
        fc = self.getcompiled(f, [])
        ret = fc()
        assert ret[0] != ret[1]

    def test_consider_constant_with_address(self):
        T = lltype.GcStruct('test')
        x = llmemory.cast_ptr_to_adr(lltype.malloc(T))
        def f():
            return len([x])
        fc = self.getcompiled(f, [])
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

        fc = self.getcompiled(f, [int], 'minimark')
        assert fc(0) == 11
        assert fc(1) == 44

    def test_int_abs(self):
        def f(x):
            return abs(x)
        fc = self.getcompiled(f, [int])
        assert fc(11) == 11
        assert fc(-22) == 22

    def test_new_erasing_pair(self):
        from rpython.rlib.rerased import new_erasing_pair
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
        fc = self.getcompiled(f, [int], 'minimark')
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
        from rpython.rlib.rsocket import inet_ntoa
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
        from rpython.rlib.entrypoint import entrypoint_highlevel
        from rpython.translator.interactive import Translation

        def f(args):
            return 3

        key = 'test_entrypoints42'
        @entrypoint_highlevel(key, [int], 'foobar')
        def g(x):
            return x + 42

        t = Translation(f, None, backend='llvm', secondaryentrypoints=key,
                        gcremovetypeptr=False)
        t.annotate()
        t.source_llvm()
        assert l('define LONG @foobar') in t.driver.llvmgen.main_ll_file.read()

    def test_export_struct(self):
        from rpython.rlib.exports import export_struct

        a = lltype.malloc(lltype.Struct('A'), immortal=True)
        export_struct('a', a._obj)

        def f():
            return len([a])
        self.getcompiled(f, [])
        assert '@a = global %A' in self.genllvm.main_ll_file.read()

    def test_export_struct_cast(self):
        from rpython.rlib.exports import export_struct
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
        self.getcompiled(f, [])
        assert '@a = global %A' in self.genllvm.main_ll_file.read()
        lltype.free(buf, 'raw')

    def test_ovf_op_in_loop(self):
        from sys import maxint
        from rpython.rlib.rarithmetic import ovfcheck
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

    def test_recursive_llhelper(self): # ported from GenC
        from rpython.rtyper.annlowlevel import llhelper
        from rpython.rtyper.lltypesystem import lltype
        from rpython.rlib.objectmodel import specialize
        FT = lltype.ForwardReference()
        FTPTR = lltype.Ptr(FT)
        STRUCT = lltype.Struct("foo", ("bar", FTPTR))
        FT.become(lltype.FuncType([lltype.Ptr(STRUCT)], lltype.Signed))

        class A:
            def __init__(self, func, name):
                self.func = func
                self.name = name
            def _freeze_(self):
                return True
            @specialize.memo()
            def make_func(self):
                f = getattr(self, "_f", None)
                if f is not None:
                    return f
                f = lambda *args: self.func(*args)
                f.c_name = self.name
                f.relax_sig_check = True
                f.__name__ = "WRAP%s" % (self.name, )
                self._f = f
                return f
            def get_llhelper(self):
                return llhelper(FTPTR, self.make_func())
        def f(s):
            if s.bar == t.bar:
                lltype.free(s, flavor="raw")
                return 1
            lltype.free(s, flavor="raw")
            return 0
        def g(x):
            return 42
        def chooser(x):
            s = lltype.malloc(STRUCT, flavor="raw")
            if x:
                s.bar = llhelper(FTPTR, a_f.make_func())
            else:
                s.bar = llhelper(FTPTR, a_g.make_func())
            return f(s)
        a_f = A(f, "f")
        a_g = A(g, "g")
        t = lltype.malloc(STRUCT, flavor="raw", immortal=True)
        t.bar = llhelper(FTPTR, a_f.make_func())
        fn = self.getcompiled(chooser, [bool])
        assert fn(True)

    def test_longfloat(self):
        py.test.skip('ctypes problem')
        def f(x):
            return rffi.cast(lltype.Bool, x)
        fc = self.getcompiled(f, [lltype.LongFloat])
        assert not fc(r_longfloat(0.0))
        assert fc(r_longfloat(1.0))

    def test_recursive_notail(self):
        def f(n):
            if n <= 0:
                return 42
            return f(n+1)
        def entry_point():
            return f(1)
        fc = self.getcompiled(entry_point, [])
        fc(expected_exception_name='StackOverflow')


class TestLowLevelTypeLLVM(_LLVMMixin, test_lltyped.TestLowLevelType):
    def getcompiled(self, func, argtypes):
        return _LLVMMixin.getcompiled(self, func, argtypes, backendopt=False)

    def test_union(self):
        py.test.skip('not supported')

    def test_llgroup_size_limit(self):
        py.test.skip('takes too long to complete')


class TestTypedLLVM(_LLVMMixin, test_typed.TestTypedTestCase):
    def getcompiled(self, func, argtypes):
        return _LLVMMixin.getcompiled(self, func, argtypes, backendopt=False)

    def test_r_dict_exceptions(self):
        py.test.skip("ordered dicts don't seem to work with refcounting")


class TestTypedOptimizedTestCaseLLVM(_LLVMMixin, test_backendoptimized
                                                 .TestTypedOptimizedTestCase):
    def test_r_dict_exceptions(self):
        py.test.skip("ordered dicts don't seem to work with refcounting")

class TestTypedOptimizedSwitchTestCaseLLVM(_LLVMMixin,
                                           test_backendoptimized
                                           .TestTypedOptimizedSwitchTestCase):
    pass


class TestLLVMRffi(BaseTestRffi, _LLVMMixin):
    def compile(self, func, argtypes, gcpolicy='ref', backendopt=True):
        fn = self.getcompiled(func, argtypes, gcpolicy, backendopt)
        def fn2(*args, **kwds):
            kwds.pop('expected_extra_mallocs', None)
            return fn(*args, **kwds)
        return fn2

    def test_string_reverse(self):
        py.test.skip('Specific to GenC')


class TestMiniMarkGCLLVM(test_newgc.TestMiniMarkGC):
    @classmethod
    def _set_backend(cls, t):
        t.ensure_backend('llvm')


class DisabledTestMiniMarkGCLLVMGCRoot(test_newgc.TestMiniMarkGC):
    @classmethod
    def _set_backend(cls, t):
        t.ensure_backend('llvm')
        t.ensure_opt('gcrootfinder', 'llvmgcroot')


class TestMiniMarkGCMostCompactLLVM(test_newgc.TestMiniMarkGCMostCompact):
    @classmethod
    def _set_backend(cls, t):
        t.ensure_backend('llvm')


class TestRefcountLLVM(_LLVMMixin, test_refcount.TestRefcount):
    def compile_func(self, fn, inputtypes, t=None):
        if t is not None:
            py.test.skip('not supported yet')
        return self.getcompiled(fn, inputtypes, gcpolicy='ref')
