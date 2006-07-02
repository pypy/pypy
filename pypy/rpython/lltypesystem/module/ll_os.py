from pypy.rpython.module.support import LLSupport
from pypy.rpython.module.ll_os import BaseOS
from pypy.rpython.lltypesystem import lltype, rtuple
from pypy.rpython.rarithmetic import intmask

n = 10
STAT_RESULT = rtuple.TUPLE_TYPE([lltype.Signed]*n).TO

class Implementation(BaseOS, LLSupport):
    
    def ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                       stat5, stat6, stat7, stat8, stat9):
        tup = lltype.malloc(STAT_RESULT)
        tup.item0 = intmask(stat0)
        tup.item1 = intmask(stat1)
        tup.item2 = intmask(stat2)
        tup.item3 = intmask(stat3)
        tup.item4 = intmask(stat4)
        tup.item5 = intmask(stat5)
        tup.item6 = intmask(stat6)
        tup.item7 = intmask(stat7)
        tup.item8 = intmask(stat8)
        tup.item9 = intmask(stat9)
        return tup
    ll_stat_result = staticmethod(ll_stat_result)

