# mostly-deprecated module

from rpython.rtyper.ootypesystem import ootype
from rpython.rtyper.ootypesystem.rtupletype import TUPLE_TYPE
from rpython.rtyper.module.ll_os_stat import PORTABLE_STAT_FIELDS

STAT_RESULT = TUPLE_TYPE([_TYPE for _name, _TYPE in PORTABLE_STAT_FIELDS])
