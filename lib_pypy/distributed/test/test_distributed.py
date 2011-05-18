
""" Controllers tests
"""

from pypy.conftest import gettestobjspace
import sys
import pytest

class AppTestDistributed(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
            "usemodules":("_stackless",)})

    def test_init(self):
        import distributed

    def test_protocol(self):
        from distributed.protocol import AbstractProtocol
        protocol = AbstractProtocol()
        for item in ("aaa", 3, u"aa", 344444444444444444L, 1.2, (1, "aa")):
            assert protocol.unwrap(protocol.wrap(item)) == item
        assert type(protocol.unwrap(protocol.wrap([1,2,3]))) is list
        assert type(protocol.unwrap(protocol.wrap({"a":3}))) is dict
        
        def f():
            pass
        
        assert type(protocol.unwrap(protocol.wrap(f))) is type(f)

    def test_method_of_false_obj(self):
        from distributed.protocol import AbstractProtocol
        protocol = AbstractProtocol()
        lst = []
        m = lst.append
        assert type(protocol.unwrap(protocol.wrap(m))) is type(m)

    def test_protocol_run(self):
        l = [1,2,3]
        from distributed.protocol import LocalProtocol
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
        
        from distributed.protocol import LocalProtocol
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

    def test_local_obj(self):
        class A(object):
            def __init__(self, x):
                self.x = x
            
            def __len__(self):
                return self.x + 8
        
        from distributed.protocol import LocalProtocol
        protocol = LocalProtocol()
        wrap = protocol.wrap
        unwrap = protocol.unwrap
        item = unwrap(wrap(A(3)))
        assert item.x == 3
        assert len(item) == 11

class AppTestDistributedTasklets(object):
    spaceconfig = {"objspace.std.withtproxy": True,
                   "objspace.usemodules._stackless": True}
    def setup_class(cls):
        #cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
        #    "usemodules":("_stackless",)})
        cls.w_test_env = cls.space.appexec([], """():
        from distributed import test_env
        return test_env
        """)
        cls.reclimit = sys.getrecursionlimit()
        sys.setrecursionlimit(100000)

    def teardown_class(cls):
        sys.setrecursionlimit(cls.reclimit)
    
    def test_remote_protocol_call(self):
        def f(x, y):
            return x + y
        
        protocol = self.test_env({"f": f})
        fun = protocol.get_remote("f")
        assert fun(2, 3) == 5

    def test_callback(self):
        def g():
            return 8
        
        def f(x):
            return x + g()
        
        protocol = self.test_env({"f":f})
        fun = protocol.get_remote("f")
        assert fun(8) == 16
    
    def test_remote_dict(self):
        #skip("Land of infinite recursion")
        d = {'a':3}
        protocol = self.test_env({'d':d})
        xd = protocol.get_remote('d')
        #assert d['a'] == xd['a']
        assert d.keys() == xd.keys()
        assert d.values() == xd.values()
        assert d == xd
        
    def test_remote_obj(self):
        class A(object):
            def __init__(self, x):
                self.x = x
            
            def __len__(self):
                return self.x + 8
        a = A(3)
        
        protocol = self.test_env({'a':a})
        xa = protocol.get_remote("a")
        assert xa.x == 3
        assert len(xa) == 11
    
    def test_remote_doc_and_callback(self):
        class A(object):
            """xxx"""
            def __init__(self):
                pass

            def meth(self, x):
                return x() + 3
        
        def x():
            return 1
        
        a = A()
        
        protocol = self.test_env({'a':a})
        xa = protocol.get_remote('a')
        assert xa.__class__.__doc__ == 'xxx'
        assert xa.meth(x) == 4

    def test_double_reference(self):
        class A(object):
            def meth(self, one):
                self.one = one
            
            def perform(self):
                return 1 + len(self.one())
        
        class B(object):
            def __call__(self):
                return [1,2,3]
        
        a = A()
        protocol = self.test_env({'a': a})
        xa = protocol.get_remote('a')
        xa.meth(B())
        assert xa.perform() == 4

    def test_frame(self):
        #skip("Land of infinite recursion")
        import sys
        f = sys._getframe()
        protocol = self.test_env({'f':f})
        xf = protocol.get_remote('f')
        assert f.f_globals.keys() == xf.f_globals.keys()
        assert f.f_locals.keys() == xf.f_locals.keys()

    def test_remote_exception(self):
        def raising():
            1/0
        
        protocol = self.test_env({'raising':raising})
        xr = protocol.get_remote('raising')
        try:
            xr()
        except ZeroDivisionError:
            import sys
            exc_info, val, tb  = sys.exc_info()
            #assert tb.tb_next is None
        else:
            raise AssertionError("Did not raise")

    def test_remote_classmethod(self):
        class A(object):
            z = 8

            @classmethod
            def x(cls):
                return cls.z

        a = A()
        protocol = self.test_env({'a':a})
        xa = protocol.get_remote("a")
        res = xa.x()
        assert res == 8

    def test_types_reverse_mapping(self):
        class A(object):
            def m(self, tp):
                assert type(self) is tp

        a = A()
        protocol = self.test_env({'a':a, 'A':A})
        xa = protocol.get_remote('a')
        xA = protocol.get_remote('A')
        xa.m(xA)

    def test_instantiate_remote_type(self):
        class C(object):
            def __init__(self, y):
                self.y = y
            
            def x(self):
                return self.y

        protocol = self.test_env({'C':C})
        xC = protocol.get_remote('C')
        xc = xC(3)
        res = xc.x()
        assert res == 3

    def test_remote_sys(self):
        import sys

        protocol = self.test_env({'sys':sys})
        s = protocol.get_remote('sys')
        l = dir(s)
        assert l

    def test_remote_file_access(self):
        skip("Descriptor logic seems broken")
        protocol = self.test_env({'f':open})
        xf = protocol.get_remote('f')
        data = xf('/etc/passwd').read()
        assert data

    def test_real_descriptor(self):
        class getdesc(object):
            def __get__(self, obj, val=None):
                if obj is not None:
                    assert type(obj) is X
                return 3

        class X(object):
            x = getdesc()

        x = X()

        protocol = self.test_env({'x':x})
        xx = protocol.get_remote('x')
        assert xx.x == 3
    
    def test_bases(self):
        class X(object):
            pass

        class Y(X):
            pass

        y = Y()
        protocol = self.test_env({'y':y, 'X':X})
        xy = protocol.get_remote('y')
        xX = protocol.get_remote('X')
        assert isinstance(xy, xX)

    def test_key_error(self):
        from distributed import ObjectNotFound
        protocol = self.test_env({})
        raises(ObjectNotFound, "protocol.get_remote('x')")

    def test_list_items(self):
        protocol = self.test_env({'x':3, 'y':8})
        assert sorted(protocol.remote_keys()) == ['x', 'y']

