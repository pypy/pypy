import os
from pypy.rpython.module.support import OOSupport
from pypy.rpython.module.ll_os import BaseOS
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rarithmetic import intmask

n = 10
fieldnames = ['item%d' % i for i in range(n)]
lltypes = [ootype.Signed]*n
fields = dict(zip(fieldnames, lltypes))    
STAT_RESULT = ootype.Record(fields)

class Implementation(BaseOS, OOSupport):
    
    def ll_stat_result(stat0, stat1, stat2, stat3, stat4,
                       stat5, stat6, stat7, stat8, stat9):
        tup = ootype.new(STAT_RESULT)
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

    def ll_os_read(cls, fd, count):
        return cls.to_rstr(os.read(fd, count))
    ll_os_read.suggested_primitive = True
