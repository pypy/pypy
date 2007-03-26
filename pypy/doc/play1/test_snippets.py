from pypy.conftest import gettestobjspace

class AppTest_pypy_c(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
            "usemodules":("_stackless",)})
        
    def test_snippet_1(self):
        from tputil import make_proxy
        history = []
        def recorder(operation):
            history.append(operation) 
            return operation.delegate()

        l = make_proxy(recorder, obj=[])

class AppTest_pypy_c_thunk(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.name": 'thunk'})

    def test_snippet_1(self):
        from __pypy__ import thunk
        def f():
            print 'computing...'
            return 6*7

        x = thunk(f)

class AppTest_pypy_c_taint(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'objspace.name': 'taint'})

    def test_snippet_1(self):
        from __pypy__ import taint
        x = taint(6)

class AppTest_pypy_cli(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'usemodules': 'clr'})

    def test_snippet_1(self):
        import clr
        ArrayList = clr.load_cli_class('System.Collections', 'ArrayList')
        obj = ArrayList()
        obj.Add(1)

class AppTest_pyrolog_c(object):
    pass

class AppTest_python(object):
    pass

class AppTest_pypy_c_jit(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{'usemodules':('pypyjit',)})

    def test_snippet_1(self):
        import time
        
        def f1(n):
            "Arbitrary test function."
            i = 0
            x = 1
            while i<n:
                j = 0
                while j<=i:
                    j = j + 1
                    x = x + (i&j)
                i = i + 1
            return x

        def test_f1():
            res = f1(211)
            print "running..."
            N = 5
            start = time.time()
            for i in range(N):
                assert f1(211) == res
            end = time.time()
            print '%d iterations, time per iteration: %s' % (N, (end-start)/N)

        import pypyjit
