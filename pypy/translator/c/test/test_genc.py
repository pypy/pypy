import autopath, sys, os, py
from pypy.rpython.lltypesystem.lltype import *
from pypy.annotation import model as annmodel
from pypy.translator.translator import TranslationContext
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.c.genc import gen_source
from pypy.translator.c.gc import NoneGcPolicy
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph
from pypy.tool.udir import udir
from pypy.translator.tool.cbuild import make_module_from_c
from pypy.translator.tool.cbuild import enable_fast_compilation
from pypy.translator.gensupp import uniquemodulename
from pypy.translator.backendopt.all import backend_optimizations
from pypy import conftest

# XXX this tries to make compiling faster for full-scale testing
# XXX tcc leaves some errors undetected! Bad!
#from pypy.translator.tool import cbuild
#cbuild.enable_fast_compilation()


def compile_db(db):
    enable_fast_compilation()  # for testing
    modulename = uniquemodulename('testing')
    targetdir = udir.join(modulename).ensure(dir=1)
    gen_source(db, modulename, str(targetdir), defines={'COUNT_OP_MALLOCS': 1})
    m = make_module_from_c(targetdir.join(modulename+'.c'),
                           include_dirs = [os.path.dirname(autopath.this_dir)])
    return m

def compile(fn, argtypes, view=False, gcpolicy=None, backendopt=True):
    t = TranslationContext()
    a = t.buildannotator()
    a.build_types(fn, argtypes)
    t.buildrtyper().specialize()
    if backendopt:
        backend_optimizations(t)
    db = LowLevelDatabase(t, gcpolicy=gcpolicy)
    entrypoint = db.get(pyobjectptr(fn))
    db.complete()
    module = compile_db(db)
    if view or conftest.option.view:
        t.view()
    compiled_fn = getattr(module, entrypoint)
    def checking_fn(*args, **kwds):
        res = compiled_fn(*args, **kwds)
        mallocs, frees = module.malloc_counters()
        assert mallocs == frees
        return res
    return checking_fn


def test_untyped_func():
    def f(x):
        return x+1
    graph = TranslationContext().buildflowgraph(f)

    F = FuncType([Ptr(PyObject)], Ptr(PyObject))
    S = GcStruct('testing', ('fptr', Ptr(F)))
    f = functionptr(F, "f", graph=graph)
    s = malloc(S)
    s.fptr = f
    db = LowLevelDatabase()
    db.get(s)
    db.complete()
    compile_db(db)


def test_func_as_pyobject():
    def f(x):
        return x*2
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()

    db = LowLevelDatabase(t)
    entrypoint = db.get(pyobjectptr(f))
    db.complete()
    module = compile_db(db)

    f1 = getattr(module, entrypoint)
    assert f1(5) == 10
    assert f1(x=5) == 10
    assert f1(-123) == -246
    assert module.malloc_counters() == (0, 0)
    py.test.raises(Exception, f1, "world")  # check that it's really typed
    py.test.raises(Exception, f1)
    py.test.raises(Exception, f1, 2, 3)
    py.test.raises(Exception, f1, 2, x=2)
    #py.test.raises(Exception, f1, 2, y=2)   XXX missing a check at the moment


def test_rlist():
    def f(x):
        l = [x]
        l.append(x+1)
        return l[0] * l[-1]
    f1 = compile(f, [int])
    assert f1(5) == 30
    assert f1(x=5) == 30


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
    assert f1(i=5) == 10
    assert f1(1) == 2
    assert f1(0) == -42
    assert f1(-1) == -42
    assert f1(-5) == -42


def test_rptr_array():
    A = GcArray(Ptr(PyObject))
    def f(i, x):
        p = malloc(A, i)
        p[1] = x
        return p[1]
    f1 = compile(f, [int, annmodel.SomePtr(Ptr(PyObject))])
    assert f1(5, 123) == 123
    assert f1(12, "hello") == "hello"


def test_runtime_type_info():
    S = GcStruct('s', ('is_actually_s1', Bool))
    S1 = GcStruct('s1', ('sub', S))
    attachRuntimeTypeInfo(S)
    attachRuntimeTypeInfo(S1)
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
        return sys
    t = TranslationContext()
    t.buildannotator().build_types(does_stuff, [])
    rtyper = t.buildrtyper()
    rtyper.attachRuntimeTypeInfoFunc(S,  rtti_S)
    rtyper.attachRuntimeTypeInfoFunc(S1, rtti_S1)
    rtyper.specialize()
    #t.view()

    db = LowLevelDatabase(t)
    entrypoint = db.get(pyobjectptr(does_stuff))
    db.complete()

    module = compile_db(db)

    f1 = getattr(module, entrypoint)
    f1()
    mallocs, frees = module.malloc_counters()
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

def test_x():
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
    from pypy.rpython import objectmodel
    def f():
        x = [1]
        y = ['b']
        objectmodel.keepalive_until_here(x,y)
        return 1

    f1 = compile(f, [])
    assert f1() == 1

# ____________________________________________________________
# test for the 'cleanup' attribute of SpaceOperations
class CleanupState(object):
    pass
cleanup_state = CleanupState()
cleanup_state.current = 1
def cleanup_g(n):
    cleanup_state.saved = cleanup_state.current
    try:
        return 10 // n
    except ZeroDivisionError:
        raise
def cleanup_h():
    cleanup_state.current += 1
def cleanup_f(n):
    cleanup_g(n)
    cleanup_h()     # the test hacks the graph to put this h() in the
                    # cleanup clause of the previous direct_call(g)
    return cleanup_state.saved * 100 + cleanup_state.current

def test_cleanup_finally():
    class DummyGCTransformer(NoneGcPolicy.transformerclass):
        def transform_graph(self, graph):
            super(DummyGCTransformer, self).transform_graph(graph)
            if graph is self.translator.graphs[0]:
                operations = graph.startblock.operations
                op_call_g = operations[0]
                op_call_h = operations.pop(1)
                assert op_call_g.opname == "direct_call"
                assert op_call_h.opname == "direct_call"
                assert op_call_g.cleanup == ((), ())
                assert op_call_h.cleanup == ((), ())
                cleanup_finally = (op_call_h,)
                cleanup_except = ()
                op_call_g.cleanup = cleanup_finally, cleanup_except
                op_call_h.cleanup = None

    class DummyGcPolicy(NoneGcPolicy):
        transformerclass = DummyGCTransformer

    f1 = compile(cleanup_f, [int], backendopt=False, gcpolicy=DummyGcPolicy)
    # state.current == 1
    res = f1(1)
    assert res == 102
    # state.current == 2
    res = f1(1)
    assert res == 203
    # state.current == 3
    py.test.raises(ZeroDivisionError, f1, 0)
    # state.current == 4
    res = f1(1)
    assert res == 405
    # state.current == 5

def test_cleanup_except():
    class DummyGCTransformer(NoneGcPolicy.transformerclass):
        def transform_graph(self, graph):
            super(DummyGCTransformer, self).transform_graph(graph)
            if graph is self.translator.graphs[0]:
                operations = graph.startblock.operations
                op_call_g = operations[0]
                op_call_h = operations.pop(1)
                assert op_call_g.opname == "direct_call"
                assert op_call_h.opname == "direct_call"
                assert op_call_g.cleanup == ((), ())
                assert op_call_h.cleanup == ((), ())
                cleanup_finally = ()
                cleanup_except = (op_call_h,)
                op_call_g.cleanup = cleanup_finally, cleanup_except
                op_call_h.cleanup = None

    class DummyGcPolicy(NoneGcPolicy):
        transformerclass = DummyGCTransformer

    f1 = compile(cleanup_f, [int], backendopt=False, gcpolicy=DummyGcPolicy)
    # state.current == 1
    res = f1(1)
    assert res == 101
    # state.current == 1
    res = f1(1)
    assert res == 101
    # state.current == 1
    py.test.raises(ZeroDivisionError, f1, 0)
    # state.current == 2
    res = f1(1)
    assert res == 202
    # state.current == 2

# this test crashes after 30 runs on my XP machine
def test_refcount_pyobj():
    def prob_with_pyobj(a=int, b=int):
        return 2, 3, long(42)

    f = compile(prob_with_pyobj, [int, int])
    ret = f(2, 3)
    for i in xrange(1000):
        print i
        f(2, 3)
