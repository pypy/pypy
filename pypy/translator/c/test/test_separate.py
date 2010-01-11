from pypy.translator.separate import export
from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CExtModuleBuilder, CLibraryBuilder, gen_forwarddecl
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import rffi, lltype
import py
import sys, os

class TestSeparation:
    def compile_function(self, func, argtypes):
        t = TranslationContext()
        t.buildannotator().build_types(func, argtypes)
        t.buildrtyper().specialize()
        builder = CExtModuleBuilder(t, func, config=t.config)
        builder.generate_source()
        builder.compile()
        return builder.get_entry_point()

    def compile_separated(self, name, **exports):
        t = TranslationContext()
        t.buildannotator()
        for funcname, func in exports.items():
            if hasattr(func, 'argtypes'):
                t.annotator.build_types(func, func.argtypes)
        t.buildrtyper().specialize()

        exported_funcptr = {}
        for funcname, func in exports.items():
            bk = t.annotator.bookkeeper
            graph = bk.getdesc(func).getuniquegraph()
            funcptr = getfunctionptr(graph)

            exported_funcptr[funcname] = funcptr

        builder = CLibraryBuilder(t, exported_funcptr, config=t.config)
        builder.generate_source()
        builder.compile()

        mod = builder.make_import_module()
        return mod

    def test_simple_call(self):
        # function exported from the 'first' module
        @export(float)
        def f(x):
            return x + 1.5
        firstmodule = self.compile_separated("first", f=f)

        # call it from a function compiled in another module
        def fn():
            return firstmodule.f(41.0)

        assert fn() == 42.5
        c_fn = self.compile_function(fn, [])
        assert c_fn() == 42.5

    def test_nested_call(self):
        # function exported from the 'first' module
        @export(float)
        def f(x):
            return x + 1.5
        firstmodule = self.compile_separated("first", f=f)

        # function exported from the 'second' module
        @export(float)
        def g(x):
            return firstmodule.f(x) / 2
        secondmodule = self.compile_separated("second", g=g)

        # call it from a function compiled in another module
        def fn():
            return secondmodule.g(41)

        if sys.platform == 'win32':
            filepath = os.path.dirname(firstmodule.__file__)
            os.environ['PATH'] = "%s;%s" % (filepath, os.environ['PATH'])

        assert fn() == 21.25
        c_fn = self.compile_function(fn, [])
        assert c_fn() == 21.25

    def test_implied_signature(self):
        # function exported from the 'first' module
        @export
        def f(x):
            return x + 1.5
        @export()
        def f2():
            f(1.0)
            f(2.0)
        firstmodule = self.compile_separated("first", f=f, f2=f2)

        # call it from a function compiled in another module
        def fn():
            return firstmodule.f(41)

        assert fn() == 42.5
        c_fn = self.compile_function(fn, [])
        assert c_fn() == 42.5

