from pypy.objspace.fake.checkmodule import checkmodule

def test_faulthandler_translates():
    checkmodule('faulthandler')
