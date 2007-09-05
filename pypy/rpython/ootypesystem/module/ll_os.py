# mostly-deprecated module

from pypy.rpython.ootypesystem import ootype

def _make_tuple(FIELDS):
    n = len(FIELDS)
    fieldnames = ['item%d' % i for i in range(n)]
    fields = dict(zip(fieldnames, FIELDS))
    return ootype.Record(fields)

from pypy.rpython.module.ll_os_stat import PORTABLE_STAT_FIELDS

STAT_RESULT = _make_tuple([_TYPE for _name, _TYPE in PORTABLE_STAT_FIELDS])
