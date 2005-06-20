import buildcache2
from pypy.objspace.std.objspace import StdObjSpace
from pypy.translator.test import rpystone
from pypy.translator.c.symboltable import getsymboltable

# __________  Entry point  __________

LOOPS = 1000000

rpystone.setslow(False)

def entry_point():
    return rpystone.pystones(LOOPS), id(rpystone.g)
    
# _____ Define and setup target _____
def target():
    return entry_point, []

# _____ Run translated _____

def run(c_entry_point):
    res = c_entry_point()
    (benchtime, stones), g_addr = res
    print "translated rpystone.pystones/fast time for %d passes = %g" % \
        (LOOPS, benchtime)
    print "This machine benchmarks at %g translated rpystone/fast pystones/second" % stones
    print "CPython:"
    benchtime, stones = rpystone.pystones(50000)
    print "rpystone.pystones/fast time for %d passes = %g" % \
        (50000, benchtime)
    print "This machine benchmarks at %g rpystone/fast pystones/second" % stones
    symtable = getsymboltable(c_entry_point.__module__)
    check_g_results(symtable, g_addr)


def check_g_results(symtable, g_addr):
    try:
        g_ptr = symtable[g_addr]
    except KeyError:
        print "No low-level equivalent of structure 'g' found."
    else:
        assert g_ptr.inst_BoolGlob == rpystone.g.BoolGlob
        assert g_ptr.inst_Char1Glob == rpystone.g.Char1Glob
        assert g_ptr.inst_Char2Glob == rpystone.g.Char2Glob
        compare_array_of_array(g_ptr.inst_Array2Glob, rpystone.g.Array2Glob)
        compare_record(g_ptr.inst_PtrGlb, rpystone.g.PtrGlb)
        compare_record(g_ptr.inst_PtrGlbNext, rpystone.g.PtrGlbNext)


def compare_array_of_array(array, pylist):
    assert len(array.items) == len(pylist)
    for i in range(len(pylist)):
        x1 = array.items[i]
        x2 = pylist[i]
        compare_array(x1, x2)

def compare_array(array, pylist):
    assert len(array.items) == len(pylist)
    for i in range(len(pylist)):
        x1 = array.items[i]
        x2 = pylist[i]
        assert x1 == x2

def compare_record(struct, pyrecord):
    if pyrecord is None:
        assert not struct
    else:
        assert struct
        compare_record(struct.inst_PtrComp, pyrecord.PtrComp)
        assert struct.inst_Discr == pyrecord.Discr
        assert struct.inst_EnumComp == pyrecord.EnumComp
        assert struct.inst_IntComp == pyrecord.IntComp
        compare_string(struct.inst_StringComp, pyrecord.StringComp)

def compare_string(str, pystr):
    assert len(str.chars) == len(pystr)
    for i in range(len(pystr)):
        assert str.chars[i] == pystr[i]

#if __name__ == "__main__":
#    # just run it without translation
#    LOOPS = 50000
#    target()
#    run(entry_point)
    
