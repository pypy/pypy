import py
import ctypes

from pypy.annotation import model, signature
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.lltypesystem import ll2ctypes
from pypy.translator.translator import TranslationContext
from pypy.translator.c import genc
from pypy.translator.interactive import Translation
from pypy.rlib.entrypoint import entrypoint
from pypy.tool.nullpath import NullPyPathLocal


def cast_to_ctypes(type):
    s_tp = signature.annotation(type)
    ll_tp = model.annotation_to_lltype(s_tp)
    return ll2ctypes.get_ctypes_type(ll_tp)

def compile(fn, argtypes, view=False, gcpolicy="ref", backendopt=True,
            annotatorpolicy=None):
    t = Translation(fn, argtypes, gc=gcpolicy, backend="c",
                    policy=annotatorpolicy)
    if not backendopt:
        t.disable(["backendopt_lltype"])
    s_res = t.annotate()
    # XXX fish
    t.driver.config.translation.countmallocs = True
    so_name = t.compile_c()
    try:
        if py.test.config.option.view:
            t.view()
    except AttributeError:
        pass
    def f(*args):
        assert len(args) == len(argtypes)
        for arg, argtype in zip(args, argtypes):
            assert isinstance(arg, argtype)
        dll = ctypes.CDLL(str(so_name))
        func = getattr(dll, 'pypy_g_' + fn.__name__)
        func.argtypes = [cast_to_ctypes(arg) for arg in argtypes]
        func.restype = cast_to_ctypes(s_res)
        return func(*args)
    f.__name__ = fn.__name__
    return f

def test_simple():
    def f(x):
        return x*2

    f1 = compile(f, [int])

    assert f1(5) == 10
    assert f1(-123) == -246

    py.test.raises(Exception, f1, "world")  # check that it's really typed


def test_dont_write_source_files():
    def f(x):
        return x*2
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()

    t.config.translation.countmallocs = True
    t.config.translation.dont_write_c_files = True
    builder = genc.CStandaloneBuilder(t, f, config=t.config)
    builder.generate_source()
    assert isinstance(builder.targetdir, NullPyPathLocal)
    for f in builder.targetdir.listdir():
        assert not str(f).endswith('.c')


def test_rlist():
    def f(x):
        l = [x]
        l.append(x+1)
        return l[0] * l[-1]
    f1 = compile(f, [int])
    assert f1(5) == 30
    #assert f1(x=5) == 30


def test_rptr():
    S = GcStruct('testing', ('x', Signed), ('y', Signed))
    def f(i):
        if i < 0:
            p = nullptr(S)
        else:
            p = malloc(S)
            p.x = i*2
        if i > 0:
            return p.x
        else:
            return -42
    f1 = compile(f, [int])
    assert f1(5) == 10
    #assert f1(i=5) == 10
    assert f1(1) == 2
    assert f1(0) == -42
    assert f1(-1) == -42
    assert f1(-5) == -42


def test_empty_string():
    A = Array(Char, hints={'nolength': True})
    p = malloc(A, 1, immortal=True)
    def f():
        return p[0]
    f1 = compile(f, [])
    assert f1() == '\x00'

def test_runtime_type_info():
    S = GcStruct('s', ('is_actually_s1', Bool), rtti=True)
    S1 = GcStruct('s1', ('sub', S), rtti=True)
    def rtti_S(p):
        if p.is_actually_s1:
            return getRuntimeTypeInfo(S1)
        else:
            return getRuntimeTypeInfo(S)
    def rtti_S1(p):
        return getRuntimeTypeInfo(S1)
    def does_stuff():
        p = malloc(S)
        p.is_actually_s1 = False
        p1 = malloc(S1)
        p1.sub.is_actually_s1 = True
        # and no crash when p and p1 are decref'ed
        return None
    t = TranslationContext()
    t.buildannotator().build_types(does_stuff, [])
    rtyper = t.buildrtyper()
    rtyper.attachRuntimeTypeInfoFunc(S,  rtti_S)
    rtyper.attachRuntimeTypeInfoFunc(S1, rtti_S1)
    rtyper.specialize()
    #t.view()

    from pypy.translator.c import genc
    t.config.translation.countmallocs = True
    builder = genc.CExtModuleBuilder(t, does_stuff, config=t.config)
    builder.generate_source()
    builder.compile()
    f1 = builder.get_entry_point()
    f1()
    mallocs, frees = builder.get_malloc_counters()()
    assert mallocs == frees


def test_str():
    def call_str(o):
        return str(o)
    f1 = compile(call_str, [object])
    lst = (1, [5], "'hello'", lambda x: x+1)
    res = f1(lst)
    assert res == str(lst)


def test_rstr():
    def fn(i):
        return "hello"[i]
    f1 = compile(fn, [int])
    res = f1(1)
    assert res == 'e'


def test_recursive_struct():
    # B has an A as its super field, and A has a pointer to B.
    class A:
        pass
    class B(A):
        pass
    def fn(i):
        a = A()
        b = B()
        a.b = b
        b.i = i
        return a.b.i
    f1 = compile(fn, [int])
    res = f1(42)
    assert res == 42

def test_recursive_struct_2():
    class L:
        def __init__(self, target):
            self.target = target
    class RL(L):
        pass
    class SL(L):
        pass
    class B:
        def __init__(self, exits):
            self.exits = exits
    def fn(i):
        rl = RL(None)
        b = B([rl])
        sl = SL(b)
    f1 = compile(fn, [int])
    f1(42)

def test_infinite_float():
    x = 1.0
    while x != x / 2:
        x *= 3.1416
    def fn():
        return x
    f1 = compile(fn, [])
    res = f1()
    assert res > 0 and res == res / 2
    def fn():
        return -x
    f1 = compile(fn, [])
    res = f1()
    assert res < 0 and res == res / 2
    class Box:

        def __init__(self, d):
            self.d = d
    b1 = Box(x)
    b2 = Box(-x)
    b3 = Box(1.5)

    def f(i):
        if i==0:
            b = b1
        elif i==1:
            b = b2
        else:
            b = b3
        return b.d

    f1 = compile(f, [int])
    res = f1(0)
    assert res > 0 and res == res / 2
    res = f1(1)
    assert res < 0 and res == res / 2
    res = f1(3)
    assert res == 1.5

def test_nan_and_special_values():
    from pypy.rlib.rfloat import isnan, isinf, isfinite, copysign
    inf = 1e300 * 1e300
    assert isinf(inf)
    nan = inf/inf
    assert isnan(nan)

    for value, checker in [
            (inf,   lambda x: isinf(x) and x > 0.0),
            (-inf,  lambda x: isinf(x) and x < 0.0),
            (nan,   isnan),
            (42.0,  isfinite),
            (0.0,   lambda x: not x and copysign(1., x) == 1.),
            (-0.0,  lambda x: not x and copysign(1., x) == -1.),
            ]:
        def f():
            return value
        f1 = compile(f, [])
        res = f1()
        assert checker(res)

        l = [value]
        def g(x):
            return l[x]
        g2 = compile(g, [int])
        res = g2(0)
        assert checker(res)

        l2 = [(-value, -value), (value, value)]
        def h(x):
            return l2[x][1]
        h3 = compile(h, [int])
        res = h3(1)
        assert checker(res)

def test_prebuilt_instance_with_dict():
    class A:
        pass
    a = A()
    a.d = {}
    a.d['hey'] = 42
    def t():
        a.d['hey'] = 2
        return a.d['hey']
    f = compile(t, [])
    assert f() == 2

def test_long_strings():
    s1 = 'hello'
    s2 = ''.join([chr(i) for i in range(256)])
    s3 = 'abcd'*17
    s4 = open(__file__, 'rb').read()
    choices = [s1, s2, s3, s4]
    def f(i, j):
        return choices[i][j]
    f1 = compile(f, [int, int])
    for i, s in enumerate(choices):
        for j, c in enumerate(s):
            assert f1(i, j) == c


def test_keepalive():
    from pypy.rlib import objectmodel
    def f():
        x = [1]
        y = ['b']
        objectmodel.keepalive_until_here(x, y)
        return 1

    f1 = compile(f, [])
    assert f1() == 1

def test_print():
    def f():
        for i in range(10):
            print "xxx"

    fn = compile(f, [])
    fn(expected_extra_mallocs=1)

def test_name():
    def f():
        return 3

    f.c_name = 'pypy_xyz_f'

    t = Translation(f, [], backend="c")
    t.annotate()
    t.compile_c()
    if py.test.config.option.view:
        t.view()
    assert 'pypy_xyz_f' in t.driver.cbuilder.c_source_filename.read()

def test_entrypoints():
    def f():
        return 3

    key = "test_entrypoints42"
    @entrypoint(key, [int], "foobar")
    def g(x):
        return x + 42

    t = Translation(f, [], backend="c", secondaryentrypoints="test_entrypoints42")
    t.annotate()
    t.compile_c()
    if py.test.config.option.view:
        t.view()
    assert 'foobar' in t.driver.cbuilder.c_source_filename.read()

def test_exportstruct():
    from pypy.rlib.exports import export_struct
    def f():
        return 42
    FOO = Struct("FOO", ("field1", Signed))
    foo = malloc(FOO, flavor="raw")
    foo.field1 = 43
    export_struct("BarStruct", foo._obj)
    t = Translation(f, [], backend="c")
    t.annotate()
    t.compile_c()
    if py.test.config.option.view:
        t.view()
    assert ' BarStruct ' in t.driver.cbuilder.c_source_filename.read()
    free(foo, flavor="raw")

def test_recursive_llhelper():
    from pypy.rpython.annlowlevel import llhelper
    from pypy.rpython.lltypesystem import lltype
    from pypy.rlib.objectmodel import specialize
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
    fn = compile(chooser, [bool])
    assert fn(True)

def test_inhibit_tail_call():
    def foobar_fn(n):
        return 42
    foobar_fn._dont_inline_ = True
    def main(n):
        return foobar_fn(n)
    #
    t = Translation(main, [int], backend="c")
    t.rtype()
    t.context._graphof(foobar_fn).inhibit_tail_call = True
    t.source_c()
    lines = t.driver.cbuilder.c_source_filename.readlines()
    for i, line in enumerate(lines):
        if '= pypy_g_foobar_fn' in line:
            break
    else:
        assert 0, "the call was not found in the C source"
    assert 'PYPY_INHIBIT_TAIL_CALL();' in lines[i+1]
