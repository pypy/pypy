# mostly-deprecated module

from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rtupletype import TUPLE_TYPE
from pypy.rpython.module.ll_os_stat import PORTABLE_STAT_FIELDS

STAT_RESULT = TUPLE_TYPE([_TYPE for _name, _TYPE in PORTABLE_STAT_FIELDS])
