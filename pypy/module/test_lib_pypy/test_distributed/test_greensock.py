import py; py.test.skip("xxx remove")
from pypy.conftest import gettestobjspace, option

def setup_module(mod):
    py.test.importorskip("pygreen")   # found e.g. in py/trunk/contrib 

class AppTestDistributedGreensock(object):
    def setup_class(cls):
        if not option.runappdirect:
            py.test.skip("Cannot run this on top of py.py because of PopenGateway")
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True,
                                       "usemodules":("_continuation",)})
        cls.w_remote_side_code = cls.space.appexec([], """():
        import sys
        sys.path.insert(0, '%s')
        remote_side_code = '''
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
'''
        return remote_side_code
        """ % str(py.path.local(__file__).dirpath().dirpath().dirpath().dirpath()))

    def test_remote_call(self):
        from distributed import socklayer
        import sys
        from pygreen.greenexecnet import PopenGateway
        gw = PopenGateway()
        rp = socklayer.spawn_remote_side(self.remote_side_code, gw)
        a = rp.get_remote("a")
        assert a.method(lambda : 13) == 16
    
    def test_remote_counting(self):
        from distributed import socklayer
        from pygreen.greensock2 import allof
        from pygreen.greenexecnet import PopenGateway
        gws = [PopenGateway() for i in range(3)]
        rps = [socklayer.spawn_remote_side(self.remote_side_code, gw)
               for gw in gws]
        counters = [rp.get_remote("count") for rp in rps]
        assert allof(*counters) == (11, 11, 11)

