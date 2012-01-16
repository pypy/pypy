from pypy.module.micronumpy import signature
from pypy.objspace.fake.checkmodule import checkmodule

def test_numpy_translates():
    # XXX: If there are signatures floating around this might explode. This fix
    # is ugly.
    signature.known_sigs.clear()
    checkmodule('micronumpy')
