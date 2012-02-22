from pypy.translator.translator import TranslationContext
from pypy.translator.c.exportinfo import export, ModuleExportInfo
from pypy.translator.c.dlltool import CLibraryBuilder
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.backendopt.all import backend_optimizations
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.test.test_llinterp import interpret
import sys
import types

class TestExportFunctions:
    def setup_method(self, method):
        self.additional_PATH = []
        # Uniquify: use the method name without the 'test' prefix.
        self.module_suffix = method.__name__[4:]

    def compile_module(self, modulename, **exports):
        modulename += self.module_suffix
        export_info = ModuleExportInfo()
        for name, obj in exports.items():
            if isinstance(obj, (type, types.ClassType)):
                export_info.add_class(name, obj)
            else:
                export_info.add_function(name, obj)

        t = TranslationContext()
        t.buildannotator()
        export_info.annotate(t.annotator)
        t.buildrtyper().specialize()
        backend_optimizations(t)

        functions = [(info.func, None)
                     for info in export_info.functions.values()]
        builder = CLibraryBuilder(t, None, config=t.config,
                                  name='lib' + modulename,
                                  functions=functions)
        if sys.platform != 'win32' and self.additional_PATH:
            builder.merge_eci(ExternalCompilationInfo(
                    link_extra=['-Wl,-rpath,%s' % path for path in
                                self.additional_PATH]))
        builder.modulename = 'lib' + modulename
        builder.generate_source()
        builder.compile()

        mod = export_info.make_import_module(builder)

        filepath = builder.so_name.dirpath()
        self.additional_PATH.append(filepath)

        return mod

    def test_simple_call(self):
        # function exported from the 'first' module
        @export(float)
        def f(x):
            return x + 42.3
        firstmodule = self.compile_module("first", f=f)
        
        # call it from a function compiled in another module
        @export()
        def g():
            return firstmodule.f(12.0)
        secondmodule = self.compile_module("second", g=g)

        assert secondmodule.g() == 54.3

    def test_implied_signature(self):
        @export  # No explicit signature here.
        def f(x):
            return x + 1.5
        @export()  # This is an explicit signature, with no argument.
        def f2():
            f(1.0)
        firstmodule = self.compile_module("first", f=f, f2=f2)
        
        @export()
        def g():
            return firstmodule.f(41)
        secondmodule = self.compile_module("second", g=g)

        assert secondmodule.g() == 42.5

    def test_pass_structure(self):
        class Struct:
            @export(float)
            def __init__(self, x):
                self.x = x + 27.4
        @export(Struct, Struct, int)
        def f(s, t, v):
            return s.x + t.x + v
        firstmodule = self.compile_module("first", f=f, Struct=Struct)
        
        @export()
        def g():
            s = Struct(3.0)
            t = firstmodule.Struct(5.5)
            return firstmodule.f(s, t, 7)
        secondmodule = self.compile_module("second", g=g)
        assert secondmodule.g() == 70.3

        @export()
        def g2():
            # Bad argument type, should not translate
            return firstmodule.f(1, 2, 3)
        raises(TypeError, self.compile_module, "third", g2=g2)

    def test_without_module_container(self):
        # It's not necessary to fetch the functions from some
        # container, the RPython calls are automatically redirected.
        class Struct:
            @export(float)
            def __init__(self, x):
                self.x = x + 23.4
        @export(Struct, Struct, int)
        def f(s, t, v):
            assert we_are_translated()
            return s.x + t.x + v
        self.compile_module("first", f=f, Struct=Struct)
        
        @export()
        def g():
            s = Struct(3.0)
            t = Struct(5.5)
            return f(s, t, 7)
        mod = self.compile_module("second", g=g)
        assert mod.g() == 62.3
        # XXX How can we check that the code of f() was not translated again?
