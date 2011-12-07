from pypy.objspace.fake.checkmodule import checkmodule


def test_itertools_module():
    checkmodule('itertools')
