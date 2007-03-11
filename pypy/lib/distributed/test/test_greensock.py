
import py
py.test.skip("Skip this till pylib trunk->dist merge")
from pypy.conftest import gettestobjspace

class AppTestDistributedGreensock(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
                                       "usemodules":("_stackless",)})
        cls.w_remote_side_code = cls.space.appexec([], """():
        import py
        remote_side_code = str(py.code.Source('''
        class A:
            def __init__(self, x):
                self.x = x
            
            def __len__(self):
                return self.x + 8

            def raising(self):
                1/0

            def method(self, x):
                return x() + self.x

        a = A(3)

        def count():
            x = 10
            # naive counting :)
            result = 1
            for i in range(x):
                result += 1
            return result
        '''))
        return remote_side_code
        """)

    def test_remote_call(self):
        from distributed import socklayer
        from py.__.net.greenexecnet import PopenGateway
        gw = PopenGateway()
        rp = socklayer.spawn_remote_side(self.remote_side_code, gw)
        a = rp.get_remote("a")
        assert a.method(lambda : 13) == 16
    
    def test_remote_counting(self):
        from distributed import socklayer
        from py.__.net.greensock2 import allof
        from py.__.net.greenexecnet import PopenGateway
        gws = [PopenGateway() for i in range(3)]
        rps = [socklayer.spawn_remote_side(self.remote_side_code, gw)
               for gw in gws]
        counters = [rp.get_remote("count") for rp in rps]
        assert allof(*counters) == (11, 11, 11)

