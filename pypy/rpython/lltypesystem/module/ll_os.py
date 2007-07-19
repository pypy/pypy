import os, errno
from pypy.rpython.module.support import LLSupport
from pypy.rpython.module.support import ll_strcpy
from pypy.rpython.module.ll_os import BaseOS
from pypy.rpython.lltypesystem import lltype, rtupletype
from pypy.rlib.rarithmetic import intmask

STAT_RESULT = rtupletype.TUPLE_TYPE([lltype.Signed]*10).TO
PIPE_RESULT = rtupletype.TUPLE_TYPE([lltype.Signed]*2).TO
WAITPID_RESULT = rtupletype.TUPLE_TYPE([lltype.Signed]*2).TO

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

    def ll_pipe_result(fd1, fd2):
        tup = lltype.malloc(PIPE_RESULT)
        tup.item0 = fd1
        tup.item1 = fd2
        return tup
    ll_pipe_result = staticmethod(ll_pipe_result)

    def ll_os_readlink(cls, path):
        from pypy.rpython.lltypesystem.rstr import mallocstr
        bufsize = 1023
        while 1:
            buffer = mallocstr(bufsize)
            n = cls.ll_readlink_into(cls, path, buffer)
            if n < bufsize:
                break
            bufsize *= 4     # overflow, try again with a bigger buffer
        s = mallocstr(n)
        ll_strcpy(s, buffer, n)
        return s

    def ll_waitpid_result(fd1, fd2):
        tup = lltype.malloc(WAITPID_RESULT)
        tup.item0 = fd1
        tup.item1 = fd2
        return tup
    ll_waitpid_result = staticmethod(ll_waitpid_result)
