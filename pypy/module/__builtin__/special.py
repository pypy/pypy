from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.rlib import rarithmetic

def _formatd(space, alt, prec, kind, x):
    formatd_max_length = rarithmetic.formatd_max_length
    if ((kind == 'g' and formatd_max_length <= 10+prec) or
        (kind == 'f' and formatd_max_length <= 53+prec)):
        raise OperationError(space.w_OverflowError,
                             space.wrap("formatted float is too long (precision too large?)"))    
    if alt:
        alt = '#'
    else:
        alt = ''

    fmt = "%%%s.%d%s" % (alt, prec, kind)
    
    return space.wrap(rarithmetic.formatd(fmt, x))
_formatd.unwrap_spec = [gateway.ObjSpace, int, int, str, float]


