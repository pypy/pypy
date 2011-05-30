from pypy.conftest import gettestobjspace

class AppTest_make_proxy:
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True})

    def test_errors(self):
        from tputil import make_proxy 
        raises(TypeError, "make_proxy(None)")
        raises(TypeError, "make_proxy(None, None)")
        def f(): pass 
        raises(TypeError, "make_proxy(f)")
        raises(TypeError, "make_proxy(f, None, None)")

    def test_repr(self):
        from tputil import make_proxy 
        l = []
        def func(operation): 
            l.append(repr(operation))
            return operation.delegate()
        tp = make_proxy(func, obj=[])
        tp.append(3)
        for rep in l:
            assert isinstance(rep, str)
            assert rep.find("list") != -1

    def test_virtual_proxy(self):
        from tputil import make_proxy 
        l = []
        tp = make_proxy(l.append, type=list)
        x = tp[0:1]
        assert len(l) == 1
        assert l[0].opname == '__getslice__'
       
    def test_simple(self):
        from tputil import make_proxy 
        record = []
        def func(operation):
            record.append(operation)
            return operation.delegate()
        l = make_proxy(func, obj=[])
        l.append(1)
        assert len(record) == 2
        i1, i2 = record 
        assert i1.opname == '__getattribute__'
        assert i2.opname == 'append' 

    def test_missing_attr(self):
        from tputil import make_proxy
        def func(operation):
            return operation.delegate()
        l = make_proxy(func, obj=[]) 
        raises(AttributeError, "l.asdasd")

    def test_proxy_double(self): 
        from tputil import make_proxy
        r1 = []
        r2 = []
        def func1(operation):
            r1.append(operation)
            return operation.delegate()
        def func2(operation):
            r2.append(operation)
            return operation.delegate()
            
        l = make_proxy(func1, obj=[])
        l2 = make_proxy(func2, obj=l)
        assert not r1 and not r2
        l2.append
        assert len(r2) == 1
        assert r2[0].opname == '__getattribute__'
        assert len(r1) == 2 
        assert r1[0].opname == '__getattribute__'
        assert r1[0].args[0] == '__getattribute__'
        assert r1[1].opname == '__getattribute__'
        assert r1[1].args[0] == 'append' 

    def test_proxy_inplace_add(self):
        r = []
        from tputil import make_proxy 
        def func1(operation):
            r.append(operation)
            return operation.delegate()

        l2 = make_proxy(func1, obj=[])
        l = l2
        l += [3]
        assert l is l2
