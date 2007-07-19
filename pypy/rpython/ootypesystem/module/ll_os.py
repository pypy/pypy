import os
from pypy.rpython.module.support import OOSupport
from pypy.rpython.module.ll_os import BaseOS
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.rarithmetic import intmask

def _make_tuple(FIELDS):
    n = len(FIELDS)
    fieldnames = ['item%d' % i for i in range(n)]
    fields = dict(zip(fieldnames, FIELDS))
    return ootype.Record(fields)

STAT_RESULT = _make_tuple([ootype.Signed]*10)
PIPE_RESULT = _make_tuple([ootype.Signed]*2)
WAITPID_RESULT = _make_tuple([ootype.Signed]*2)

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

    def ll_pipe_result(fd1, fd2):
        tup = ootype.new(PIPE_RESULT)
        tup.item0 = fd1
        tup.item1 = fd2
        return tup
    ll_pipe_result = staticmethod(ll_pipe_result)

    def ll_os_readlink(cls, path):
        return cls.to_rstr(os.readlink(path))
    ll_os_readlink.suggested_primitive = True

    def ll_waitpid_result(fd1, fd2):
        tup = ootype.new(WAITPID_RESULT)
        tup.item0 = fd1
        tup.item1 = fd2
        return tup
    ll_waitpid_result = staticmethod(ll_waitpid_result)
