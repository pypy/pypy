from pypy.rpython.lltypesystem import lltype, rffi, llmemory

def values_array(TP, size):
    ATP = lltype.GcArray(TP)
    
    class ValuesArray(object):
        def __init__(self):
            self.ar = lltype.malloc(ATP, size, zero=True, immortal=True)

        def get_addr_for_num(self, i):
            return rffi.cast(lltype.Signed, lltype.direct_ptradd(
                lltype.direct_arrayitems(self.ar), i))

        def setitem(self, i, v):
            self.ar[i] = v

        def getitem(self, i):
            return self.ar[i]

        def _freeze_(self):
            return True

    return ValuesArray()
