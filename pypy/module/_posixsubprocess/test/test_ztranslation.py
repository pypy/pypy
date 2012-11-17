from pypy.objspace.fake.checkmodule import checkmodule

def test_posixsubprocess_translates():
    checkmodule('_posixsubprocess')
