from pypy.translator.separate import export
from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CExtModuleBuilder, CLibraryBuilder
from pypy.translator.c import separate
from pypy.translator.tool.cbuild import ExternalCompilationInfo
import py
import sys, os, types

class TestSeparation:
    def setup_method(self, method):
        self.additional_PATH = []

        class S:
            @export(float)
            def __init__(self, x):
                self.x = x

        # functions exported from the 'first' module
        @export(float)
        def newS(x):
            return S(x)

        @export(S, S, int)
        def f2S(s, t, v):
            return s.x + t.x + v

        self.S = S
        self.newS = newS
        self.f2S = f2S

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

        table = separate.ExportTable()
        for name, obj in exports.items():
            if isinstance(obj, (type, types.ClassType)):
                table.exported_class[name] = obj
            else:
                table.exported_function[name] = obj
        table.annotate_exported_functions(t.annotator)

        t.buildrtyper().specialize()

        table.compute_exported_repr(t.rtyper)

        exported_funcptr = table.get_exported_functions(t.annotator)

        builder = CLibraryBuilder(t, exported_funcptr, config=t.config)
        builder.generate_source()
        node_names = dict(
            (funcname, builder.db.get(funcptr))
            for funcname, funcptr in builder.entrypoint.items())
        builder.compile()

        mod = table.make_import_module(builder, node_names)

        if sys.platform == 'win32':
            filepath = os.path.dirname(builder.so_name)
            self.additional_PATH.append(filepath)

        return mod

    def call_exported(self, func):
        if sys.platform == 'win32':
            for path in self.additional_PATH:
                os.environ['PATH'] = "%s;%s" % (path, os.environ['PATH'])

        def fn():
            return func()

        return fn

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
        fn = self.call_exported(lambda: secondmodule.g(41))

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
        firstmodule = self.compile_separated("first", f=f, f2=f2)

        # call it from a function compiled in another module
        def fn():
            return firstmodule.f(41)

        assert fn() == 42.5
        c_fn = self.compile_function(fn, [])
        assert c_fn() == 42.5

    def test_pass_structure(self):
        firstmodule = self.compile_separated("first", f=self.f2S, S=self.S)
        S = self.S

        @export()
        def g():
            s = S(41.0)
            t = S(25.5)
            return firstmodule.f(s, t, 7)
        secondmodule = self.compile_separated("second", g=g)

        fn = self.call_exported(secondmodule.g)

        assert fn() == 73.5
        c_fn = self.compile_function(fn, [])
        assert c_fn() == 73.5

    def test_create_structure(self):
        firstmodule = self.compile_separated(
            "first", newS=self.newS, S=self.S, f=self.f2S)

        @export()
        def g():
            s = firstmodule.newS(41.0)
            t = firstmodule.S(25.5)
            return firstmodule.f(s, t, 7)
        secondmodule = self.compile_separated("second", g=g)

        fn = self.call_exported(secondmodule.g)

        assert fn() == 73.5
        c_fn = self.compile_function(fn, [])
        assert c_fn() == 73.5

    def test_structure_attributes(self):
        py.test.skip("WIP")
        firstmodule = self.compile_separated(
            "first", S=self.S)

        @export()
        def g():
            s = firstmodule.S(41.5)
            s.x /= 2
            return s.x
        secondmodule = self.compile_separated("second", g=g)

        fn = self.call_exported(secondmodule.g)

        assert fn() == 20.25
        c_fn = self.compile_function(fn, [])
        assert c_fn() == 20.25

