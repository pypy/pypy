from pypy.translator.translator import Translator
from pypy.translator.tool.cbuild import skip_missing_compiler
from pypy.translator.c.genc import CExtModuleBuilder

class TestBoehmTestCase:

    def getcompiled(self, func):
        from pypy.translator.c.gc import BoehmGcPolicy
        t = Translator(func, simplifying=True)
        # builds starting-types from func_defs 
        argstypelist = []
        if func.func_defaults:
            for spec in func.func_defaults:
                if isinstance(spec, tuple):
                    spec = spec[0] # use the first type only for the tests
                argstypelist.append(spec)
        a = t.annotate(argstypelist)
        a.simplify()
        t.specialize()
        t.checkgraphs()
        def compile():
            cbuilder = CExtModuleBuilder(t, gcpolicy=BoehmGcPolicy)
            c_source_filename = cbuilder.generate_source()
            cbuilder.compile()
            cbuilder.import_module()    
            return cbuilder.get_entry_point()
        return skip_missing_compiler(compile)


    def DONTtest_malloc_a_lot(self):
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = [1] * 10
                j = 0
                while j < 20:
                    j += 1
                    a.append(j)
        fn = self.getcompiled(malloc_a_lot)
        fn()
