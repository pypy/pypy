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

