import py
from pypy.translator.translator import TranslationContext
from pypy.translator.tool.cbuild import skip_missing_compiler
from pypy.translator.c.genc import CExtModuleBuilder

py.test.skip("boehm test is fragile wrt. the number of dynamically loaded libs")


def getcompiled(func):
    from pypy.translator.c.gc import BoehmGcPolicy
    t = TranslationContext(simplifying=True)
    # builds starting-types from func_defs 
    argstypelist = []
    if func.func_defaults:
        for spec in func.func_defaults:
            if isinstance(spec, tuple):
                spec = spec[0] # use the first type only for the tests
            argstypelist.append(spec)
    a = t.buildannotator().build_types(func, argstypelist)
    t.buildrtyper().specialize()
    t.checkgraphs()
    def compile():
        cbuilder = CExtModuleBuilder(t, func, gcpolicy=BoehmGcPolicy)
        c_source_filename = cbuilder.generate_source()
        cbuilder.compile()
        cbuilder.import_module()    
        return cbuilder.get_entry_point()
    return skip_missing_compiler(compile)


def test_malloc_a_lot():
    def malloc_a_lot():
        i = 0
        while i < 10:
            i += 1
            a = [1] * 10
            j = 0
            while j < 20:
                j += 1
                a.append(j)
    fn = getcompiled(malloc_a_lot)
    fn()

def test__del__():
    class State:
        pass
    s = State()
    class A(object):
        def __del__(self):
            s.a_dels += 1
    class B(A):
        def __del__(self):
            s.b_dels += 1
    class C(A):
        pass
    def f():
        s.a_dels = 0
        s.b_dels = 0
        A()
        B()
        C()
        A()
        B()
        C()
        return s.a_dels * 10 + s.b_dels
    fn = getcompiled(f)
    res = f()
    assert res == 42
    res = fn() #does not crash
    res = fn() #does not crash
    assert 0 <= res <= 42 # 42 cannot be guaranteed
