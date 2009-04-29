import py
import os
import os.path
from pypy.tool import udir
from pypy.translator.cli.rte import Target
from pypy.translator.cli.carbonpython import DllDef, export, collect_entrypoints,\
     collect_class_entrypoints, compile_dll
from pypy.translator.cli.test.runtest import CliFunctionWrapper, CliTest

TEMPLATE = """
using System;
using System.Collections;
class CarbonPytonTest {
    public static void Main() {
        %s
    }
}
"""

class TestCarbonPython(CliTest):
    
    def _csharp(self, source, references=[], netmodules=[]):
        tmpfile = udir.udir.join('tmp.cs')
        tmpfile.write(TEMPLATE % source)
        flags = ['/r:%s' % ref for ref in references]
        flags += ['/addmodule:%s' % mod for mod in netmodules]
        
        class MyTarget(Target):
            SOURCES = [str(tmpfile)]
            FLAGS = flags
            OUTPUT = 'tmp.exe'
            SRC_DIR = str(udir.udir)

        func = CliFunctionWrapper(MyTarget.get())
        return func()

    def test_compilation(self):
        res = self._csharp('Console.WriteLine(42);')
        assert res == 42

    def test_func_namespace(self):
        def foo(x):
            return x+1
        def bar(x):
            return foo(x)
        foo._namespace_ = 'MyNamespace.MyClass'
        bar._namespace_ = 'MyClass'
        res = self.interpret(bar, [41], backendopt=False)
        assert res == 42

    def test_simple_functions(self):
        def foo(x):
            return x+1
        def bar(x):
            return x*2
        dll = DllDef('test', 'Test', [(foo, [int]),
                                      (bar, [int])])
        dll.compile()
        res = self._csharp('Console.WriteLine("{0}, {1}", Test.foo(42), Test.bar(42));', ['test'])
        assert res == (43, 84)

    def test_export(self):
        @export(int, float)
        def foo(x, y):
            pass
        @export(int, float, namespace='test')
        def bar(x, y):
            pass
        @export
        def baz():
            pass

        assert foo._inputtypes_ == (int, float)
        assert not hasattr(foo, '_namespace_')
        assert bar._inputtypes_ == (int, float)
        assert bar._namespace_ == 'test'
        assert baz._inputtypes_ == ()

    def test_collect_entrypoints(self):
        @export(int, float)
        def foo(x, y):
            pass
        def bar(x, y):
            pass
        mydict = dict(foo=foo, bar=bar, x=42)
        entrypoints = collect_entrypoints(mydict)
        assert entrypoints == [(foo, (int, float))]

    def test_collect_class_entrypoints(self):
        class NotExported:
            def __init__(self):
                pass
            
        class MyClass:
            @export
            def __init__(self):
                pass
            @export(int)
            def foo(self, x):
                return x

        assert collect_class_entrypoints(NotExported) == []
        entrypoints = collect_class_entrypoints(MyClass)
        assert len(entrypoints) == 2
        assert entrypoints[0][1] == () # __init__ inputtypes
        assert entrypoints[1][1] == (MyClass, int) # foo inputtypes
        
    def test_compile_class(self):
        py.test.skip('This test fails every other day. No clue why :-(')
        class MyClass:
            @export(int)
            def __init__(self, x):
                self.x = x
            @export(int, int)
            def add(self, y, z):
                return self.x + y + z
        MyClass.__module__ = 'Test' # put the class in the Test namespace

        entrypoints = collect_entrypoints({'MyClass': MyClass})
        dll = DllDef('test', 'Test', entrypoints)
        dll.compile()
        res = self._csharp("""
            Test.MyClass obj = new Test.MyClass();
            obj.__init__(39);
            Console.WriteLine(obj.add(1, 2));
        """, ['test'])
        assert res == 42

    def test_export_cliclass(self):
        from pypy.translator.cli.dotnet import CLR
        
        @export(CLR.System.Collections.ArrayList, int)
        def getitem(obj, i):
            return obj.get_Item(i)

        entrypoints = collect_entrypoints({'getitem': getitem})
        dll = DllDef('test', 'Test', entrypoints)
        dll.compile()
        res = self._csharp("""
            ArrayList obj = new ArrayList();
            obj.Add(42);
            Console.WriteLine(Test.getitem(obj, 0));
        """, ['test'])
        assert res == 42

    def test_compile_dll(self):
        cwd, _ = os.path.split(__file__)
        mylib_py = os.path.join(cwd, 'mylib.py')
        compile_dll(mylib_py, copy_dll=False)
        res = self._csharp("""
            Console.WriteLine(mylib.sum(20, 22));
        """, ['mylib'])
        assert res == 42

    def test_compile_dll_alternative_name(self):
        cwd, _ = os.path.split(__file__)
        mylib_py = os.path.join(cwd, 'mylib.py')
        compile_dll(mylib_py, 'mylibxxx.dll', copy_dll=False)
        res = self._csharp("""
            Console.WriteLine(mylibxxx.sum(20, 22));
        """, ['mylibxxx'])
        assert res == 42

    def test_compile_netmodule(self):
        def foo(x):
            return x+1
        dll = DllDef('mymodule', 'Test', [(foo, [int])], isnetmodule=True)
        dll.compile()
        res = self._csharp('Console.WriteLine("{0}", Test.foo(41));',
                           netmodules = ['mymodule'])
        
