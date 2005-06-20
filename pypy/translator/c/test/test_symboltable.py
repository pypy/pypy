from pypy.translator.translator import Translator
from pypy.translator.c.symboltable import getsymboltable

def test_simple():
    glist = [4, 5, 6]
    def f(x):
        return glist[x]
    t = Translator(f)
    t.annotate([int])
    t.specialize()

    f = t.ccompile()
    assert f(1) == 5
    assert f(2) == 6

    symtable = getsymboltable(f.__module__)
    debug_list = symtable['g_list']    # XXX find a way to find this name
    assert len(debug_list.items) == 3
    assert debug_list.items[0] == 4
    assert debug_list.items[1] == 5
    assert debug_list.items[2] == 6
