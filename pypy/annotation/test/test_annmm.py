import autopath

from pypy.objspace.std.multimethod import *
from pypy.annotation.annrpython import RPythonAnnotator

class W_Root(object):
    pass

class W_Int(W_Root):
    pass

class W_Str(W_Root):
    pass


str_w = MultiMethodTable(1, root_class=W_Root, argnames_before=['space'])
int_w = MultiMethodTable(1, root_class=W_Root, argnames_before=['space'])


def int_w__Int(space, w_x):
    assert space == 'space'
    assert isinstance(w_x, W_Int)
    return 1

def str_w__Str(space, w_x):
    assert space == 'space'
    assert isinstance(w_x, W_Str)
    return "string"

int_w.register(int_w__Int, W_Int)
str_w.register(str_w__Str, W_Str)


def setup_module(mod):
    typeorder = {
        W_Int: [(W_Int, None)],
        W_Str: [(W_Str, None)],
        }
    mod.typeorder = typeorder
    mod.str_w1 = str_w.install('__str_w', [typeorder])
    mod.int_w1 = int_w.install('__int_w', [typeorder])


def test_str_w_ann():
    a = RPythonAnnotator()
    s1 = a.build_types(str_w1,[str, W_Str])
    s2 = a.build_types(str_w1,[str, W_Root])
    assert s1.knowntype == str
    assert s2.knowntype == str
    
def test_int_w_ann():
    a = RPythonAnnotator()
    s1 = a.build_types(int_w1,[str, W_Int])
    s2 = a.build_types(int_w1,[str, W_Str])
    assert s1.knowntype == int
    assert s2.knowntype == int
    
    
