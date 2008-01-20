from pypy.conftest import gettestobjspace
from pypy.module.clr.test.test_clr import skip_if_not_pythonnet

skip_if_not_pythonnet()

class AppTestDotnet:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('clr', ))
        cls.space = space

    def test_list_of_namespaces_and_classes(self):
        import clr
        ns, classes, generics = clr.get_assemblies_info()
        
        assert 'System' in ns
        assert 'System.Collections' in ns
        assert 'System.Runtime' in ns
        assert 'System.Runtime.InteropServices' in ns

        assert 'System' not in classes
        assert 'System.Math' in classes
        assert 'System.Collections.ArrayList' in classes

        assert 'System.Collections.Generic.List' in classes
        assert generics['System.Collections.Generic.List'] == 'System.Collections.Generic.List`1'

    def test_import_hook_simple(self):
        mscorlib = 'mscorlib, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089'
        import clr
        import System.Math

        assert System.Math.Abs(-5) == 5
        assert System.Math.Pow(2, 5) == 2**5

        Math = clr.load_cli_class(mscorlib, 'System', 'Math')
        assert Math is System.Math

        import System
        a = System.Collections.Stack()
        a.Push(3)
        a.Push(44)
        sum = 0
        for i in a:
           sum += i
        assert sum == 3+44

        import System.Collections.ArrayList
        ArrayList = clr.load_cli_class(mscorlib, 'System.Collections', 'ArrayList')
        assert ArrayList is System.Collections.ArrayList

    def test_ImportError(self):
        def fn():
            import non_existent_module
        raises(ImportError, fn)

    def test_import_twice(self):
        import System
        s1 = System
        import System
        assert s1 is System

    def test_lazy_import(self):
        import System
        System.Runtime.InteropServices # does not raise attribute error

    def test_generic_class_import(self):
        import System.Collections.Generic.List

    def test_import_from(self):
        from System.Collections import ArrayList

    def test_AddReferenceByPartialName(self):
        import clr
        clr.AddReferenceByPartialName('System.Xml')
        import System.Xml.XmlReader # does not raise
        
    def test_AddReference_early(self):
        import clr
        clr.AddReferenceByPartialName('System.Xml')
