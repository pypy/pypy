from pypy.conftest import gettestobjspace

class AppTestTPListproxy:
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True})
       
    def test_listproxy_basic(self):
        from tputil import make_instance_proxy 
        record = []
        def func(invocation):
            record.append(invocation)
            return invocation.perform()
        l = make_instance_proxy([], func) 
        l.append(1)
        assert len(record) == 2
        i1, i2 = record 
        assert i1.opname == '__getattribute__'
        assert i2.opname == 'append' 

    def test_proxy_double(self): 
        from tputil import make_instance_proxy 
        r1 = []
        r2 = []
        def func1(invocation):
            r1.append(invocation)
            return invocation.perform()
        def func2(invocation):
            r2.append(invocation)
            return invocation.perform()
            
        l = make_instance_proxy([], func1) 
        l2 = make_instance_proxy(l, func2) 
        assert not r1 and not r2
        l2.append
        assert len(r2) == 1
        assert r2[0].opname == '__getattribute__'
        assert len(r1) == 2 
        assert r1[0].opname == '__getattribute__'
        assert r1[0].args[0] == '__getattribute__'
        assert r1[1].opname == '__getattribute__'
        assert r1[1].args[0] == 'append' 
