from pypy.conftest import gettestobjspace

class AppTestTPListproxy:
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True})
        cls.w_BaseDispatcher = cls.space.appexec([],"""
            (): 
                from tputil import BaseDispatcher
                return BaseDispatcher 
        """)
       
    def test_listproxy_basic(self):
        x = []
        wrapper = self.BaseDispatcher(x)
        assert wrapper.realobj is x 
        l = wrapper.proxyobj
        assert type(l) is list
        l.append(1)
        l.extend([2,3])
        assert l == [1,2,3]
        assert x == l
    
    def test_listproxy_getattribute(self):
        disp = self.BaseDispatcher([])
        meth = disp.proxyobj.append 
        assert meth.im_self == disp.proxyobj
        meth = disp.proxyobj.__getattribute__
        assert meth.im_self == disp.proxyobj

    def test_listproxy_hook(self):
        class MyBaseDispatcher(self.BaseDispatcher):
            def op___getitem__(self, *args, **kwargs):
                return 42 
        l = MyBaseDispatcher([]).proxyobj
        assert l[0] == 42
        assert l[-1] == 42
