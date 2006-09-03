
""" test debug generation transformation
"""

from pypy.translator.transformer.test.test_basictransform import \
    transform_function, interp_fun
from pypy.translator.transformer.debug import DebugTransformer, traceback_handler

from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.transformer.basictransform import BasicTransformer
from pypy import conftest
from pypy.rpython import llinterp
from pypy.objspace.flow import model
from pypy.translator.unsimplify import copyvar

import py
py.test.skip("llinterp does not like my transformations")

def g():
    pass

def test_basic_debug():
    def f():
        g()
    
    def wrapper():
        f()
        return traceback_handler.tb
    
    t = transform_function(DebugTransformer, wrapper, [])
    res = interp_fun(t, wrapper)
    real_res = [s._items['item0']._str for s in res._list]
    assert len(real_res) == 0

def test_debug_raising():
    #py.test.skip("llinterp does some strange things with operations order")
    def a():
        raise ValueError()
    
    def b():
        a()
    
    def c():
        b()
    
    def wrapper():
        try:
            c()
        except:
            pass
        return traceback_handler.tb
    
    t = transform_function(DebugTransformer, wrapper)
    res = interp_fun(t, wrapper)
    real_res = [s._items['item0']._str for s in res._list]
    assert len(real_res) == 3

def test_debug_double_raising():
    py.test.skip("strange llinterp stuff")
    def aaa(i):
        if i:
            raise TypeError()
    
    def zzz(i):
        aaa(i)
    
    def bbb(i):
        try:
            zzz(i)
        except TypeError:
            pass
    
    def ccc(i):
        bbb(i)
    
    def wrapper(i):
        ccc(i)
        return traceback_handler.tb
    
    t = transform_function(DebugTransformer, wrapper, [int])
    res = interp_fun(t, wrapper, [3])
    real_res = [s._items['item0']._str for s in res._list]
    assert len(real_res) == 3
