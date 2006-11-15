
""" Controllers tests
"""

from pypy.conftest import gettestobjspace

class AppTestNoProxy(object):
    disabled = True
    def test_init(self):
        raises(ImportError, "import distributed")

class AppTestDistributed(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True})

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

    def test_remote_protocol_call(self):
        def f(x, y):
            return x + y
        
        import types
        from distributed import RemoteProtocol, bootstrap
        import sys

        data = []
        result = []
        protocol = RemoteProtocol(result.append, data.pop)
        data += [("finished", protocol.wrap(5)), protocol.wrap(f)]
        fun = protocol.get_remote("f")
        assert isinstance(fun, types.FunctionType)
        assert fun(2, 3) == 5
