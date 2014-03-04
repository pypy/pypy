from pypy.objspace.fake.checkmodule import checkmodule

def test__ffi_translates():
    checkmodule('_rawffi.alt')
