
from pypy.objspace.fake.checkmodule import checkmodule

def test_numpy_translates():
    checkmodule('micronumpy')
