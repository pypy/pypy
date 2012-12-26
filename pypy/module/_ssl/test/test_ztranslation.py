from pypy.objspace.fake.checkmodule import checkmodule

def test__ssl_translates():
    checkmodule('_ssl')
