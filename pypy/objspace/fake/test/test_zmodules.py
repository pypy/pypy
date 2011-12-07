from pypy.objspace.fake.checkmodule import checkmodule


def test__bisect():
    checkmodule('_bisect')

def test__random():
    checkmodule('_random')

def test_cStringIO():
    checkmodule('cStringIO')

def test_itertools():
    checkmodule('itertools')
