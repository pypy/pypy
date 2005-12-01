from pypy.translator.c.symboltable import getsymboltable
from pypy.translator.c.test import test_typed

getcompiled = test_typed.TestTypedTestCase().getcompiled

def test_simple():
    glist = [4, 5, 6]
    def fn(x=int):
        return glist[x], id(glist)

    f = getcompiled(fn)
    res, addr = f(1)
    assert res == 5

    symtable = getsymboltable(f.__module__)
    debug_list = symtable[addr]
    debug_items = debug_list.ll_items()
    assert len(debug_items) == 3
    assert debug_items[0] == 4
    assert debug_items[1] == 5
    assert debug_items[2] == 6
