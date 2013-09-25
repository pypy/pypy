from pypy.objspace.fake.checkmodule import checkmodule

def test_cpyext_translates():
    checkmodule('cpyext', '_ffi')
