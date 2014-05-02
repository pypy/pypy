from rpython.rlib import rmpdec
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import (TypeDef, GetSetProperty, descr_get_dict,
    descr_set_dict, descr_del_dict)


IEEE_CONTEXT_MAX_BITS = rmpdec.MPD_IEEE_CONTEXT_MAX_BITS
MAX_PREC = rmpdec.MPD_MAX_PREC

class W_Decimal(W_Root):
    pass

W_Decimal.typedef = TypeDef(
    'Decimal')
