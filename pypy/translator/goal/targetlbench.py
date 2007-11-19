
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.llmemory import cast_ptr_to_adr, raw_memclear,\
     raw_memcopy, sizeof, itemoffsetof

TP = lltype.GcArray(lltype.Signed)

def f(x):
    if 1:
        a = lltype.malloc(TP, x)
        for i in range(x):
            a[i] = i
        b = lltype.malloc(TP, x, zero=False)
        for j in range(1000):
            #for i in range(x):
            #    b[i] = a[i]
            baseofs = itemoffsetof(TP, 0)
            onesize = sizeof(TP.OF)
            size = baseofs + onesize*(x - 1)
            raw_memcopy(cast_ptr_to_adr(b)+baseofs, cast_ptr_to_adr(a)+baseofs, size)
    else:
        a = []
        for i in range(x):
            a.append(i)
    return 0

def entry_point(argv):
    print f(int(argv[1]))
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

if __name__ == '__main__':
    import sys
    entry_point(sys.argv)
