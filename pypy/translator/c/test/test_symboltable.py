from pypy.translator.translator import Translator
from pypy.translator.c.symboltable import getsymboltable

def test_simple():
    glist = [4, 5, 6]
    def f(x):
        return glist[x], id(glist)
    t = Translator(f)
    t.annotate([int])
    t.specialize()

    f = t.ccompile()
    res, addr = f(1)
    assert res == 5

    symtable = getsymboltable(f.__module__)
    debug_list = symtable[addr]
    assert len(debug_list.items) == 3
    assert debug_list.items[0] == 4
    assert debug_list.items[1] == 5
    assert debug_list.items[2] == 6
