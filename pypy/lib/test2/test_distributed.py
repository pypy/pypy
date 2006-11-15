
""" Controllers tests
"""

from pypy.conftest import gettestobjspace

class AppTestNoProxy(object):
    disabled = True
    def test_init(self):
        raises(ImportError, "import distributed")

class AppTestDistributed(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
            "usemodules":("_stackless",)})

    def test_init(self):
        import distributed
        distributed.proxy

    def test_protocol(self):
        from distributed import AbstractProtocol
        protocol = AbstractProtocol()
        for item in ("aaa", 3, u"aa", 344444444444444444L, 1.2, (1, "aa")):
            assert protocol.unwrap(protocol.wrap(item)) == item
        assert type(protocol.unwrap(protocol.wrap([1,2,3]))) is list
        assert type(protocol.unwrap(protocol.wrap({"a":3}))) is dict
        
        def f():
            pass
        
        assert type(protocol.unwrap(protocol.wrap(f))) is type(f)

    def test_protocol_run(self):
        l = [1,2,3]
        from distributed import LocalProtocol
        protocol = LocalProtocol()
        wrap = protocol.wrap
        unwrap = protocol.unwrap
        item = unwrap(wrap(l))
        assert len(item) == 3
        assert item[2] == 3
        item += [1,1,1]
        assert len(item) == 6

    def test_protocol_call(self):
        def f(x, y):
            return x + y
        
        from distributed import LocalProtocol
        protocol = LocalProtocol()
        wrap = protocol.wrap
        unwrap = protocol.unwrap
        item = unwrap(wrap(f))
        assert item(3, 2) == 5

    def test_simulation_call(self):
        def f(x, y):
            return x + y
        
        import types
        from distributed import RemoteProtocol
        import sys

        data = []
        result = []
        protocol = RemoteProtocol(result.append, data.pop)
        data += [("finished", protocol.wrap(5)), ("finished", protocol.wrap(f))]
        fun = protocol.get_remote("f")
        assert isinstance(fun, types.FunctionType)
        assert fun(2, 3) == 5

    def test_remote_protocol_call(self):
        def f(x, y):
            return x + y
        
        from distributed import test_env
        protocol = test_env({"f": f})
        fun = protocol.get_remote("f")
        assert fun(2, 3) == 5

    def test_callback(self):
        def g():
            return 8
        
        def f(x):
            return x + g()
        
        from distributed import test_env
        protocol = test_env({"f":f})
        fun = protocol.get_remote("f")
        assert fun(8) == 16

    def test_local_obj(self):
        class A:
            def __init__(self, x):
                self.x = x
            
            def __len__(self):
                return self.x + 8
        
        from distributed import LocalProtocol
        protocol = LocalProtocol()
        wrap = protocol.wrap
        unwrap = protocol.unwrap
        item = unwrap(wrap(A(3)))
        assert item.x == 3
        assert len(item) == 11

    def test_remote_obj(self):
        class A:
            def __init__(self, x):
                self.x = x
            
            def __len__(self):
                return self.x + 8
        a = A(3)
        
        from distributed import test_env
        protocol = test_env({'a':a})
        xa = protocol.get_remote("a")
        assert xa.x == 3
        assert len(xa) == 11
    
