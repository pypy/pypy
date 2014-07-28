from pypy.objspace.fake.checkmodule import checkmodule

def test_lzma_translates():
    checkmodule('_lzma')
