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
    debug_items = debug_list.ll_items()
    assert len(debug_items) == 3
    assert debug_items[0] == 4
    assert debug_items[1] == 5
    assert debug_items[2] == 6
